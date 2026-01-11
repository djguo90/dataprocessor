
# # 小学单模重刷冒烟
# python main.py --phase 小学 --tran_script_key '.tranScript' --save_dir /mnt/pan8T/temp_djguo/存量库清洗-小学单模重刷/冒烟1w --stage 保存爬取输入 --orig_data_path /mnt/pan8T/temp_djguo/存量库清洗-小学单模重刷/primary_repair_transcript_1w.json


# 初中单模历史库过滤
# -----------------------------------------------------------------
# -----------------------------------------------------------------
## latex过滤结果

# # for i in {0..53}
# # for i in 3 9 10 14 15 19 20 23 25 27 30 32 33 34 35 37 40 44 46 47 48 49 51 
# for i in 27
# do
#     echo ${i}
#     nohup python /mnt/pan8T/temp_djguo/存量库清洗-初中单模/代码/main.py \
#         --part=${i} \
#         --stage=latex过滤结果 \
#         --orig_data_path=/mnt/pan8T/topic_repair/jianwang25_topic_source_data/xiaoshu_sm/all_json/part-$(printf "%05d" "$i")-3e3ce051-8a5e-40ad-997f-eac4fbd5e7af-c000 \
#         > ./logs/latex_${i}.log 2>&1 &
# done

# ## 解析过滤结果
# nohup python /mnt/pan8T/temp_djguo/存量库清洗-初中单模/代码/main.py \
# --stage=解析过滤结果 \
# --analysis_result_path=/mnt/pan8T/temp_jiahe3/results/junior/3kw/final_result_check_latex_html/*json \
# > ./logs/analysis.log 2>&1 &

# ## 视频过滤结果
# for i in {0..53}
# do
#     echo ${i}
#     nohup python /mnt/pan8T/temp_djguo/存量库清洗-初中单模/代码/main.py \
#         --part=${i} \
#         --stage=爬取输出结果 \
#         > ./logs/video_${i}.log 2>&1 &
# done


## 综合过滤

# for i in {0..26}
# do
#     echo ${i}
#     nohup python /mnt/pan8T/temp_djguo/存量库清洗-初中单模/代码/main.py \
#         --part=${i} \
#         --stage=综合过滤结果 \
#         --orig_data_path=/mnt/pan8T/topic_repair/jianwang25_topic_source_data/xiaoshu_sm/all_json/part-$(printf "%05d" "$i")-3e3ce051-8a5e-40ad-997f-eac4fbd5e7af-c000 \
#         > ./logs/综合过滤_${i}.log 2>&1 &
# done

# for i in {28..53}
# do
#     echo ${i}
#     nohup python /mnt/pan8T/temp_djguo/存量库清洗-初中单模/代码/main.py \
#         --part=${i} \
#         --stage=综合过滤结果 \
#         --orig_data_path=/mnt/pan8T/topic_repair/jianwang25_topic_source_data/xiaoshu_sm/all_json/part-$(printf "%05d" "$i")-3e3ce051-8a5e-40ad-997f-eac4fbd5e7af-c000 \
#         > ./logs/综合过滤_${i}.log 2>&1 &
# done

# for i in 21 24 42 4
# do
#     echo ${i}
#     nohup python /mnt/pan8T/temp_djguo/存量库清洗-初中单模/代码/main.py \
#         --part=${i} \
#         --stage=综合过滤结果 \
#         --orig_data_path=/mnt/pan8T/topic_repair/jianwang25_topic_source_data/xiaoshu_sm/all_json/part-$(printf "%05d" "$i")-3e3ce051-8a5e-40ad-997f-eac4fbd5e7af-c000 \
#         > ./logs/综合过滤_${i}.log 2>&1 &
# done

# for i in 27
# do
#     echo ${i}
#     nohup python /mnt/pan8T/temp_djguo/存量库清洗-初中单模/代码/main.py \
#         --part=${i} \
#         --stage=综合过滤结果 \
#         --orig_data_path=/mnt/pan8T/topic_repair/jianwang25_topic_source_data/xiaoshu_sm/all_json/part-$(printf "%05d" "$i")-3e3ce051-8a5e-40ad-997f-eac4fbd5e7af-c000 \
#         > ./logs/综合过滤_${i}.log 2>&1 &
# done

# ## 查看分布
# for i in $(ls -v /mnt/pan8T/temp_djguo/存量库清洗-初中单模/正式批次/初中单模视频综合过滤结果/*)
# do
#     # echo ${i}
#     grep '"tran_script_operate_type": "null"' ${i} |jq .tran_script_version |sort |uniq -c |grep "latex"
# done

# -----------------------------------------------------------------
# -----------------------------------------------------------------