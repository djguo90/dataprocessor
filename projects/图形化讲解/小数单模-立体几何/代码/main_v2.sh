

## 拆分数据

# python /mnt/pan8T/temp_djguo/dataprocessor/projects/图形化讲解/小数单模-立体几何/代码/main.py \
# --save_dir /mnt/pan8T/temp_djguo/dataprocessor/data/图形化讲解 \
# --tixing 小数单模-立体几何 \
# --stage 拆分数据 \
# --test_count 200 \
# --other_count 500 \
# --n_test_part 2

## phase1 爬取输入

python /mnt/pan8T/temp_djguo/dataprocessor/projects/图形化讲解/小数单模-立体几何/代码/main_v2.py \
--save_dir /mnt/pan8T/temp_djguo/dataprocessor/data/图形化讲解 \
--tixing 小数单模-立体几何 \
--stage phase1爬取输入 \
--data_type 试标 \
--part 1 \
--id_key_path .topic_id \
--content_key_path .video_content \
--analysis_key_path .analysis.html \
--phase1_prompt_version v5

for i in {3..5}
do
    python /mnt/pan8T/temp_djguo/dataprocessor/projects/图形化讲解/小数单模-立体几何/代码/main_v2.py \
    --save_dir /mnt/pan8T/temp_djguo/dataprocessor/data/图形化讲解 \
    --tixing 小数单模-立体几何 \
    --stage phase1爬取输入 \
    --data_type 训练集 \
    --part ${i} \
    --id_key_path .topic_id \
    --content_key_path .video_content \
    --analysis_key_path .analysis.html \
    --phase1_prompt_version v5
done

## phase2 爬取输入

# python /mnt/pan8T/temp_djguo/dataprocessor/projects/图形化讲解/小数单模-立体几何/代码/main_v2.py \
# --save_dir /mnt/pan8T/temp_djguo/dataprocessor/data/图形化讲解 \
# --tixing 小数单模-立体几何 \
# --stage phase2爬取输入 \
# --data_type 试标 \
# --part 1 \
# --id_key_path .topic_id \
# --content_key_path .video_content \
# --analysis_key_path .analysis.html \
# --phase1_prompt_version v4 \
# --phase2_prompt_version v4

# for i in {1..5}
# do
#     python /mnt/pan8T/temp_djguo/dataprocessor/projects/图形化讲解/小数单模-立体几何/代码/main_v2.py \
#     --save_dir /mnt/pan8T/temp_djguo/dataprocessor/data/图形化讲解 \
#     --tixing 小数单模-立体几何 \
#     --stage phase2爬取输入 \
#     --data_type 训练集 \
#     --part ${i} \
#     --id_key_path .topic_id \
#     --content_key_path .video_content \
#     --analysis_key_path .analysis.html \
#     --phase1_prompt_version v4 \
#     --phase2_prompt_version v4
# done

## 转manim格式

# python /mnt/pan8T/temp_djguo/dataprocessor/projects/图形化讲解/小数单模-立体几何/代码/main_v2.py \
# --save_dir /mnt/pan8T/temp_djguo/dataprocessor/data/图形化讲解 \
# --tixing 小数单模-立体几何 \
# --stage 转Manim格式 \
# --data_type 试标 \
# --part 1 \
# --id_key_path .topic_id \
# --content_key_path .video_content \
# --analysis_key_path .analysis.html \
# --phase1_prompt_version v4 \
# --phase2_prompt_version v4 \
# --html_template_path /mnt/pan8T/temp_djguo/dataprocessor/projects/图形化讲解/小数单模-立体几何/代码/htmlTemplate.html

# for i in {1..5}
# do
#     python /mnt/pan8T/temp_djguo/dataprocessor/projects/图形化讲解/小数单模-立体几何/代码/main_v2.py \
#     --save_dir /mnt/pan8T/temp_djguo/dataprocessor/data/图形化讲解 \
#     --tixing 小数单模-立体几何 \
#     --stage 转Manim格式 \
#     --data_type 训练集 \
#     --part ${i} \
#     --id_key_path .topic_id \
#     --content_key_path .video_content \
#     --analysis_key_path .analysis.html \
#     --phase1_prompt_version v4 \
#     --phase2_prompt_version v4 \
#     --html_template_path /mnt/pan8T/temp_djguo/dataprocessor/projects/图形化讲解/小数单模-立体几何/代码/htmlTemplate.html
# done

## 第四步处理
# cd /mnt/pan8T/temp_djguo/dataprocessor/projects/图形化讲解/小数单模-立体几何/视频生产步骤
# python 4.generate_manim_from_nljson.py \
#     --source /mnt/pan8T/temp_djguo/dataprocessor/data/图形化讲解/小数单模-立体几何/4.manim可处理格式_v2/小数单模-立体几何_训练集_manim可处理格式_part001_p1v4_p2v4_matched_484.json \
#     --question /mnt/pan8T/temp_djguo/dataprocessor/data/图形化讲解/小数单模-立体几何/4.manim可处理格式_v2/小数单模-立体几何_训练集_manim可处理格式_part001_p1v4_p2v4_matched_484.json \
#     --output /mnt/pan8T/temp_djguo/dataprocessor/data/图形化讲解/小数单模-立体几何/5.视频结果_v2/小数单模-立体几何_训练集_manim可处理格式_part001_p1v4_p2v4_matched_484
# python 4.generate_manim_from_nljson.py \
#     --source /mnt/pan8T/temp_djguo/dataprocessor/data/图形化讲解/小数单模-立体几何/4.manim可处理格式_v2/小数单模-立体几何_训练集_manim可处理格式_part002_p1v4_p2v4_matched_481.json \
#     --question /mnt/pan8T/temp_djguo/dataprocessor/data/图形化讲解/小数单模-立体几何/4.manim可处理格式_v2/小数单模-立体几何_训练集_manim可处理格式_part002_p1v4_p2v4_matched_481.json \
#     --output /mnt/pan8T/temp_djguo/dataprocessor/data/图形化讲解/小数单模-立体几何/5.视频结果_v2/小数单模-立体几何_训练集_manim可处理格式_part002_p1v4_p2v4_matched_481
# python 4.generate_manim_from_nljson.py \
#     --source /mnt/pan8T/temp_djguo/dataprocessor/data/图形化讲解/小数单模-立体几何/4.manim可处理格式_v2/小数单模-立体几何_训练集_manim可处理格式_part003_p1v4_p2v4_matched_488.json \
#     --question /mnt/pan8T/temp_djguo/dataprocessor/data/图形化讲解/小数单模-立体几何/4.manim可处理格式_v2/小数单模-立体几何_训练集_manim可处理格式_part003_p1v4_p2v4_matched_488.json \
#     --output /mnt/pan8T/temp_djguo/dataprocessor/data/图形化讲解/小数单模-立体几何/5.视频结果_v2/小数单模-立体几何_训练集_manim可处理格式_part003_p1v4_p2v4_matched_488
# python 4.generate_manim_from_nljson.py \
#     --source /mnt/pan8T/temp_djguo/dataprocessor/data/图形化讲解/小数单模-立体几何/4.manim可处理格式_v2/小数单模-立体几何_训练集_manim可处理格式_part004_p1v4_p2v4_matched_492.json \
#     --question /mnt/pan8T/temp_djguo/dataprocessor/data/图形化讲解/小数单模-立体几何/4.manim可处理格式_v2/小数单模-立体几何_训练集_manim可处理格式_part004_p1v4_p2v4_matched_492.json \
#     --output /mnt/pan8T/temp_djguo/dataprocessor/data/图形化讲解/小数单模-立体几何/5.视频结果_v2/小数单模-立体几何_训练集_manim可处理格式_part004_p1v4_p2v4_matched_492
# python 4.generate_manim_from_nljson.py \
#     --source /mnt/pan8T/temp_djguo/dataprocessor/data/图形化讲解/小数单模-立体几何/4.manim可处理格式_v2/小数单模-立体几何_训练集_manim可处理格式_part005_p1v4_p2v4_matched_489.json \
#     --question /mnt/pan8T/temp_djguo/dataprocessor/data/图形化讲解/小数单模-立体几何/4.manim可处理格式_v2/小数单模-立体几何_训练集_manim可处理格式_part005_p1v4_p2v4_matched_489.json \
#     --output /mnt/pan8T/temp_djguo/dataprocessor/data/图形化讲解/小数单模-立体几何/5.视频结果_v2/小数单模-立体几何_训练集_manim可处理格式_part005_p1v4_p2v4_matched_489

# ## 第五步处理
# cd /mnt/pan8T/temp_djguo/dataprocessor/projects/图形化讲解/小数单模-立体几何/视频生产步骤
# # python 5.render_manim_batch_1.py
# # python 5.render_manim_batch_2.py
# python 5.render_manim_batch_3.py 
# python 5.render_manim_batch_4.py 
# python 5.render_manim_batch_5.py 


## phase2 保存题目和解析

# for i in {3..3}
# do
#     /mnt/onet/temp_djguo/miniforge3/bin/python /mnt/pan8T/temp_djguo/dataprocessor/projects/图形化讲解/小数单模-立体几何/代码/main_v2.py \
#     --save_dir /mnt/pan8T/temp_djguo/dataprocessor/data/图形化讲解 \
#     --tixing 小数单模-立体几何 \
#     --stage 获得题目解析文本 \
#     --data_type 训练集 \
#     --part ${i} \
#     --id_key_path .topic_id \
#     --content_key_path .video_content \
#     --analysis_key_path .analysis.html \
#     --phase1_prompt_version v4 \
#     --phase2_prompt_version v4 \
#     --rendered_ids_path /mnt/pan8T/temp_djguo/dataprocessor/data/图形化讲解/小数单模-立体几何/5.视频结果_v2/小数单模-立体几何_训练集_视频结果_part003_p1v4_p2v4_matched_488/rendered_ids.txt
# done