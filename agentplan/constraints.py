"""Land-use requirements and feasibility checks for communities and complete plans."""
from .landuse import cates_str2list, landuse2area, cate2conflicts

def evaluate_requirements(gdf, focus_areas=None) -> list:
    if focus_areas is None:
        focus_areas = gdf['id'].tolist()

    results = []
    for i in gdf.index:
        area_id = int(gdf.loc[i, 'id'])
        area_type = gdf.loc[i, 'type']
        area_size = gdf.loc[i, 'area']

        if area_id not in focus_areas:
            continue

        if area_type in ['vacant', 'changeable']:

            errors = []
            cur_cates_str = gdf.loc[i, 'POI_cates']
            cur_cates = cates_str2list(cur_cates_str)
            if len(cur_cates) == 0: # if empty, meet requirement
                continue
            cur_area = sum([landuse2area[x] for x in cur_cates])
            result = {'id':area_id, 'POI_cates':cur_cates_str, 'area':area_size}

            # area limit
            if cur_area > area_size:
                errors.append('Area exceeded')

            # conflict cates
            conflict_pairs = []
            for x in cur_cates:
                for y in cate2conflicts[x]:
                    if y in cur_cates:
                        pairs = tuple(sorted([x, y]))
                        if pairs not in conflict_pairs:
                            conflict_pairs.append(pairs)
            for x, y in conflict_pairs:
                errors.append(f'Conflict: {x} & {y} cannot coexist in the same area.')
                
            if len(errors)>0:
                result['errors'] = errors
                results.append(result)
    return results

def get_feasible_cates(cur_cates: list, area_size) -> list: # given current POI types and area size, return additional POI types that can be added

    cur_area = sum([landuse2area[x] for x in cur_cates])
    available_area = area_size - cur_area
    # get conflict cates
    conflict_cates = []
    for x in cur_cates:
        conflict_cates.extend(cate2conflicts[x])
    conflict_cates = list(set(conflict_cates))
    
    feasible_cates = []
    for k,v in landuse2area.items():
        if (k != 'residential') and (k not in cur_cates) and (v <= available_area) and (k not in conflict_cates):
            feasible_cates.append(k)
    return feasible_cates

def check_feasible_areas(gdf, focus_areas=None) -> list: # 仅检查focus_areas中的区域
    if focus_areas is None:
        focus_areas = gdf['id'].tolist()

    feasible_areas = []
    for i in gdf.index:
        area_id = gdf.loc[i, 'id']
        area_type = gdf.loc[i, 'type']
        area_size = gdf.loc[i, 'area']
        if area_id not in focus_areas:
            continue
        if area_type in ['vacant', 'changeable']:
            cur_cates_str = gdf.loc[i, 'POI_cates']
            cur_cates = cates_str2list(cur_cates_str)
            feasible_cates = get_feasible_cates(cur_cates, area_size)
            if len(feasible_cates)>0:
                feasible_areas.append([area_id, cur_cates, feasible_cates])
    return feasible_areas

def evaluate_all_requirements(gdf):
    results = []
    for i in gdf.index:
        area_id = gdf.loc[i, 'id']
        area_type = gdf.loc[i, 'type']
        area_size = gdf.loc[i, 'area']

        if area_type in ['vacant', 'changeable']:

            errors = []
            cur_cates_str = gdf.loc[i, 'POI_cates']
            cur_cates = cates_str2list(cur_cates_str)
            if len(cur_cates) == 0: # if empty, meet requirement
                continue
            cur_area = sum([landuse2area[x] for x in cur_cates])
            result = {'id':area_id, 'POI_cates':cur_cates_str, 'area':area_size}

            # area limit
            if cur_area > area_size:
                errors.append('Area exceeded')

            # conflict cates
            conflict_pairs = []
            for x in cur_cates:
                for y in cate2conflicts[x]:
                    if y in cur_cates:
                        pairs = tuple(sorted([x, y]))
                        if pairs not in conflict_pairs:
                            conflict_pairs.append(pairs)
            for x, y in conflict_pairs:
                errors.append(f'Conflict: {x} & {y} cannot coexist in the same area.')
                
            if len(errors)>0:
                result['errors'] = errors
                results.append(result)
    return results

def check_area_requirements(cur_cates: list, area_size) -> bool:
    cur_area = sum([landuse2area[x] for x in cur_cates])

    # area limit
    if cur_area > area_size:
        return False

    # conflict cates
    conflict_pairs = []
    for x in cur_cates:
        for y in cate2conflicts[x]:
            if y in cur_cates:
                pairs = tuple(sorted([x, y]))
                if pairs not in conflict_pairs:
                    conflict_pairs.append(pairs)
    if len(conflict_pairs)>0:
        return False

    return True

def contain_cates(row, cates): # whether the row contains any of the cates
    POI_cates = row['POI_cates']
    if POI_cates is None:
        return False
    for x in cates:
        if x in POI_cates:
            return True
    return False
