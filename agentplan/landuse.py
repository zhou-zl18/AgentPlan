"""Land-use categories, required areas, and category conversions."""

# requirements
landuse2id={
    'residential':1,
    'life service':2,
    'office':3,
    'park':4,
    'school':5,
    'educational facility':6,
    'hospital':7,
    'medical facility':8,
    'recreation':9,
    'restaurant':10,
    'shopping':11
}
landuse2area={
    'residential':20000,
    'life service':2000,
    'office':10000,
    'park':15000,
    'school':10000,
    'educational facility':4000,
    'hospital':10000,
    'medical facility':4000,
    'recreation':2000,
    'restaurant':2000,
    'shopping':2000
}

cate2conflicts = {
    'residential':[],
    'life service':[],
    'office':[],
    'park':[],
    'school':['hospital'],
    'educational facility':[],
    'hospital':['school'],
    'medical facility':[],
    'recreation':[],
    'restaurant':[],
    'shopping':[]
}

def cates_str2list(cates_str): # 'residential,office' -> ['residential','office']
    if cates_str is None or cates_str == '':
        return []
    POI_cates = sorted(cates_str.split(','))
    return POI_cates

def cates_list2str(cates_list): # ['residential','office'] -> 'residential,office'
    POI_cates = sorted(cates_list)
    return ','.join(POI_cates)
