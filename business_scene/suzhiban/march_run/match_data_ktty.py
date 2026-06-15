

import pandas as pd
import time
import threading
from business_scene.suzhiban.utils.info_extractor import wash_pending_content, split_thread_data
from math import ceil
# 按地域比例抽取若干条。看效果如何。如果效果不行就直接按地市维度来做。
import random
from business_scene.check_data import analysis_data
from business_scene.check_data import run_inference
from business_scene.suzhiban.complaint_judge_front.run_complaint_judge_front_new import front_complaint
from business_scene.suzhiban.complaint_judge_front.complaint_rules import ktty_company_scene, ktty_province_scene
from business_scene.suzhiban.march_run.sale_apis import run_pipeline
from business_scene.suzhiban.march_run.rules_save import ktty_rule_set


df = pd.read_excel("szb_3月_营销服务类_测试数据_30.xlsx", engine="openpyxl")


def get_result(identity_num, rough_result):
    if "无法判断" in rough_result:
        res = "无法判断"
    elif "集约" in rough_result:
        if "不集约" in rough_result:
            res = "下派"
        else:
            res = "不下派"
    elif "不下派" in rough_result:
        res = "不下派"
    else:
        res = "下派"
    print(f"res: {res}, id: {identity_num}, input: {rough_result}")
    return res

def run_total_inference(identity_num, region, extract_content, prod_one_desc, prod_num_new, rule_set):
    def _run_1(identity_num, result, extract_content, index1, index2):
        this_result, reason = front_complaint(extract_content, ktty_province_scene, ktty_company_scene)
        result[index1] = get_result(identity_num, this_result)
        result[index2] = reason
    def _run_2(identity_num, result, region, extract_content, index1, index2):
        retry = 1
        this_result = '无法判断'
        reason = "fail to run"
        while retry:
            try:
                this_result, reason = run_pipeline(identity_num, extract_content, prod_num_new, region, prod_one_desc)
                break
            except Exception as e:
                retry -= 1
                time.sleep(0.1)
                print(e)
                print(f"fail run {identity_num}")
        result[index1] = get_result(identity_num, this_result)
        result[index2] = reason
    def _run_3(result, rule_set, extract_content, index):
        result[index] = get_result(identity_num, run_inference(rule_set, extract_content))

    thread_pool = []
    result = ['', '', '', '', '']
    thread_pool.append(threading.Thread(target=_run_1, args=(identity_num, result, extract_content, 0,1,)))
    thread_pool.append(threading.Thread(target=_run_2, args=(identity_num, result, region, extract_content, 2,3,)))
    thread_pool.append(threading.Thread(target=_run_3, args=(result, rule_set, extract_content, 4,)))
    for t in thread_pool:
        t.start()
    for t in thread_pool:
        t.join()
    return result

def run_row_data(df, rule_set, result, start_index, end_index):
    for i in range(start_index, end_index):
        row_data = df.iloc[i]
        identity_num = row_data['service_order_id']
        region = row_data['region_name']
        content_1 = row_data['appeal_prod_name']
        pending_content = row_data['accept_content']
        prod_one_desc = row_data['prod_one_desc']
        prod_num_new = row_data['prod_num_new']
        content = wash_pending_content(row_data['appeal_prod_name'], '', row_data['accept_content'])
        extract_content = content + f"\n所属区域：{region}"
        # extract_content = row_data['抽取内容'] + f"\n所属区域：{region}"
        to_assign = row_data['last_self_deal']
        inference_result = run_total_inference(identity_num, region, extract_content, prod_one_desc, prod_num_new, rule_set)
        local_result = [identity_num, region, content_1, pending_content, extract_content, to_assign]
        local_result.extend(inference_result)
        print(f"index: {i}, end: {end_index}, true: {to_assign}, result: {inference_result}")
        result[i] = local_result


newdf = df
data_size = len(newdf)
thread_num = 10
thread_pool = []
thread_indices = split_thread_data(data_size, thread_num)
result = [[] for _ in range(data_size)]

for i in range(thread_num):
    thread_pool.append(threading.Thread(target=run_row_data, args=(newdf, ktty_rule_set, result, thread_indices[i], thread_indices[i + 1],)))
for t in thread_pool:
    t.start()
for t in thread_pool:
    t.join()


unmatch_result, FN_result, FT_result = analysis_data(result, True)


new_df = pd.DataFrame(result, columns=['id', '地域', '一级目录', '投诉内容', '抽取内容', "真实标签", "人工规则判断", "人工规则判断解释", "销售品判断", "销售品判断解释", "自学习规则判断", "推理标签"])
new_df.to_excel("szb_3月_开通停用类_推理结果_use_channel.xlsx", index=False, engine="openpyxl")



