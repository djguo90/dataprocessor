

## 拆分数据

# python /mnt/pan8T/temp_djguo/dataprocessor/projects/图形化讲解/小数单模-立体几何/代码/main.py \
# --save_dir /mnt/pan8T/temp_djguo/dataprocessor/data/图形化讲解 \
# --tixing 小数单模-立体几何 \
# --stage 拆分数据 \
# --test_count 200 \
# --other_count 500 \
# --n_test_part 2

## phase1 爬取输入

# python /mnt/pan8T/temp_djguo/dataprocessor/projects/图形化讲解/小数单模-立体几何/代码/main.py \
# --save_dir /mnt/pan8T/temp_djguo/dataprocessor/data/图形化讲解 \
# --tixing 小数单模-立体几何 \
# --stage phase1爬取输入 \
# --data_type 试标 \
# --part 1 \
# --id_key_path .topic_id \
# --content_key_path .video_content \
# --analysis_key_path .analysis.html \
# --phase1_prompt_version v3

## phase2 爬取输入

python /mnt/pan8T/temp_djguo/dataprocessor/projects/图形化讲解/小数单模-立体几何/代码/main.py \
--save_dir /mnt/pan8T/temp_djguo/dataprocessor/data/图形化讲解 \
--tixing 小数单模-立体几何 \
--stage phase2爬取输入 \
--data_type 试标 \
--part 1 \
--id_key_path .topic_id \
--content_key_path .video_content \
--analysis_key_path .analysis.html \
--phase1_prompt_version v3 \
--phase2_prompt_version v3

## 转manim格式

# python /mnt/pan8T/temp_djguo/dataprocessor/projects/图形化讲解/小数单模-立体几何/代码/main.py \
# --save_dir /mnt/pan8T/temp_djguo/dataprocessor/data/图形化讲解 \
# --tixing 小数单模-立体几何 \
# --stage 转Manim格式 \
# --data_type 试标 \
# --part 1 \
# --id_key_path .topic_id \
# --content_key_path .video_content \
# --analysis_key_path .analysis.html \
# --phase1_prompt_version v3 \
# --phase2_prompt_version v3 \
# --html_template_path /mnt/pan8T/temp_djguo/dataprocessor/projects/图形化讲解/小数单模-立体几何/代码/htmlTemplate.html

## phase2 保存题目和解析

# /mnt/onet/temp_djguo/miniforge3/bin/python /mnt/pan8T/temp_djguo/dataprocessor/projects/图形化讲解/小数单模-立体几何/代码/main.py \
# --save_dir /mnt/pan8T/temp_djguo/dataprocessor/data/图形化讲解 \
# --tixing 小数单模-立体几何 \
# --stage 获得题目解析文本 \
# --data_type 试标 \
# --part 1 \
# --id_key_path .topic_id \
# --content_key_path .video_content \
# --analysis_key_path .analysis.html \
# --phase1_prompt_version v3 \
# --phase2_prompt_version v3
