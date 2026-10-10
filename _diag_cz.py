import pandas as pd, re, glob

# 复用脚本里的区域映射口径
REGION_ORDER = ['美洲区','欧洲区','亚太区','FBU HRBP Dept.','其他']
def _formal_major(l3, l4):
    if l3 == 'FBU HRBP Dept.':
        return 'FBU HRBP Dept.'
    mapping = {'美洲区':['美国区','加拿大区','墨西哥区','巴西区','智利区'],
               '欧洲区':['英国区','德国区','捷克区','法国区','波兰区','西班牙区','意大利区'],
               '亚太区':['澳洲区','日本区','韩国区','东南亚区','印度区']}
    for maj, subs in mapping.items():
        if l4 in subs or any(l4.startswith(s) for s in subs):
            return maj
    return '其他'

def region_of(l3,l4):
    if l3 == 'FBU HRBP Dept.':
        return l4
    core = re.sub(r'(HRBP部|行政部|渠道部|交付管理部|商务部|财务部)$','',l4)
    return core if core else l4

FILES = [
    r'D:\Documents\Downloads\正式工-7月考勤记录.xlsx',
    r'D:\Documents\Downloads\正式工-6月考勤记录.xlsx',
    r'D:\Documents\Desktop\AI做每月人力数据\T+1确认及时性\正式工-考勤记录-10.1-10.6-及时性.xlsx',
    r'D:\Documents\Desktop\AI做每月人力数据\T+1确认及时性\正式工-考勤记录-10.7-及时性.xlsx',
]

cz_total=0
cz_abn=0
cz_abn_both_empty=0
cz_abn_one_empty=0
cz_abn_none_empty=0
sample=[]
for f in FILES:
    df = pd.read_excel(f, sheet_name='考勤记录')
    df['_d'] = pd.to_datetime(df['考勤日期'], errors='coerce')
    for _, r in df.iterrows():
        d=r['_d']
        if pd.isna(d): continue
        l3 = str(r['三级部门']).strip() if pd.notna(r['三级部门']) else ''
        l4 = str(r['四级部门']).strip() if pd.notna(r['四级部门']) else ''
        if ('财务部' in l3) or ('财务部' in l4): continue
        if not l4: continue
        if l3=='FBU HRBP Dept.':
            if l4=='美洲支持HRBP组': continue
            region=l4
        else:
            region=region_of(l3,l4)
        if region!='捷克区': continue
        cz_total+=1
        st=str(r['考勤状态'])
        yc=str(r['异常备注'])
        bz=str(r['备注'])
        has_lc=('迟到' in yc or '早退' in yc or '迟到' in bz or '早退' in bz)
        first = '' if pd.isna(r['首打卡']) else str(r['首打卡'])
        last = '' if pd.isna(r['末打卡']) else str(r['末打卡'])
        fE = not first.strip()
        lE = not last.strip()
        if st=='异常':
            cz_abn+=1
            if fE and lE:
                cz_abn_both_empty+=1
                if len(sample)<8:
                    sample.append((str(d.date()), st, yc[:30], repr(first), repr(last)))
            elif fE or lE:
                cz_abn_one_empty+=1
            else:
                cz_abn_none_empty+=1

print('捷克区 总记录:', cz_total)
print('捷克区 异常记录:', cz_abn)
print('  其中 首末都空:', cz_abn_both_empty, ' 仅其一空:', cz_abn_one_empty, ' 都不空:', cz_abn_none_empty)
print('当前会被判为[未及时](异常且非迟到早退)且首末都空的样本:')
for s in sample:
    print('  ', s)
