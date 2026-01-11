

## 初中单模

### 质量检查爬取输入

for i in {0..53}
do 
    echo $(printf "%05d" ${i})
    nohup python /mnt/pan8T/temp_djguo/dataprocessor/projects/数学刷库/main.py \
    --phase 初中 \
    --part ${i} \
    --save_dir /mnt/pan8T/temp_djguo/dataprocessor/data/初数单模刷库 \
    --stage 保存爬取输入 \
    --orig_data_path /mnt/pan8T/topic_repair/jianwang25_topic_source_data/xiaoshu_sm/all_json/part-$(printf "%05d" ${i})-3e3ce051-8a5e-40ad-997f-eac4fbd5e7af-c000 \
    > /mnt/pan8T/temp_djguo/dataprocessor/data/初数单模刷库/logs/保存爬取输入_part-$(printf "%05d" ${i}).log 2>&1 &
done