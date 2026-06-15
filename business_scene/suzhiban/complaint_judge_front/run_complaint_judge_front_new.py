

from business_scene.suzhiban.utils.utils import judge_whether_contain_complaint_type

def front_complaint(complaint_content, province_scene, company_scene):
    unmatchment =judge_whether_contain_complaint_type(complaint_content, province_scene)
    if unmatchment:
        return "集约", unmatchment
    unmatchment = judge_whether_contain_complaint_type(complaint_content, company_scene)
    if unmatchment:
        return "不集约", unmatchment
    return "无法判断", ''