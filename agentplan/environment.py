"""Planning environment and update history."""
from .landuse import cates_list2str, cates_str2list

class Environment:
    def __init__(self, init_gdf, agentdf) -> None:
        self.gdf = init_gdf.copy()
        self.agentdf = agentdf.copy()

        # record update history
        self.gdf_history = [self.gdf.copy()]
        self.gdf_update_records = []

        self.community2areas = {} # {community_id: [area_ids]}
        self.finished_communities = [] # [community_id]

    def add_update_record(self, update_record): # update_record: [planner input, plan_json]
        self.gdf_update_records.append(update_record)

    def update_area(self, area_id:int, POI_cates:list): # 强制将area_id的POI替换为POI_cates
        POI_cates_str = cates_list2str(POI_cates)
        self.gdf.loc[self.gdf['id']==area_id, 'POI_cates'] = POI_cates_str
        return self.gdf
        
    def update_gdf_by_json(self, land2use:dict): # 如果新旧POI类型有重复，则认为是新的，否则直接old+new
        for k,v in land2use.items():
            try: # 'Area 1'
                area_id = int(k.split(' ')[1])
            except: # '1'
                area_id = int(k)
            if v is None:
                v = []
                
            cur_cates_str = self.gdf.loc[self.gdf['id']==area_id, 'POI_cates'].iloc[0]
            cur_cates = cates_str2list(cur_cates_str)

            area_size = self.gdf.loc[self.gdf['id']==area_id, 'area'].iloc[0]
            
            # 如果v和cur_cates有重复，则认为是v
            intersection = set(v) & set(cur_cates)
            if intersection:
                POI_cates_str = cates_list2str(v)
            elif len(v) == 0:
                POI_cates_str = cates_list2str(v)
            else:
                # 直接old+new
                new_cates = list(set(cur_cates+v))
                POI_cates_str = cates_list2str(new_cates)

            self.gdf.loc[self.gdf['id']==area_id, 'POI_cates'] = POI_cates_str

        self.gdf_history.append(self.gdf.copy())

        return self.gdf
    
    
    def update_gdf_by_gdf(self, new_gdf):
        for area_id in new_gdf['id']:
            POI_cates = new_gdf[new_gdf['id']==area_id]['POI_cates'].iloc[0]
            self.gdf.loc[self.gdf['id']==area_id,'POI_cates'] = POI_cates
        
        self.gdf_history.append(self.gdf.copy())
        
        return self.gdf
