# 步骤1 激活环境
```
source ~/mathenv/bin/activate
```

# 步骤2 规则修复和过滤部分数据
- 脚本：3.filter_matched_only.py
- 脚本输入数据格式：
```json
{"id": "xxx", "answer": "```json\n(一阶段结果)\n```   ```json\n(二阶段结果)\n```"}
```
**说明**：代码逻辑是用pattern = "json\n(.*?)\n"分别匹配到第一阶段结果和第二阶段结果，暂未修改代码逻辑，所以如果是分步骤做的可以合并在一起作为输入。
- 执行方法：
```shell
python 3.filter_matched_only.py --source your_result_file.json
```
- 脚本输出：
1. your_result_file_bad_ids.txt               #被筛掉的数据id
2. your_result_file_matched_{data_num}.json   #被留下来的数据（下一步的输入）
   
# 步骤3 manim python脚本生成
- 脚本：4.generate_manim_from_nljson.py
- 需要修改的变量：
1. SOURCE_JSON_PATH = your_result_file_matched_{data_num}.json  #步骤2输出的文件 
2. QUESTION_BANK_PATH = your_result_file_source_data.json   
该数据格式：
```json
{"id": "xxx", "input": {"content": "题目题干", "analyse": "讲题模型输出结果（offline格式，有displayContent和explainContent的那个）"}, }
```
3. OUTPUT_ROOT = your_output_dir # 输出目录
- 执行方法：
```shell
python 4.generate_manim_from_nljson.py
```
- 脚本输出：
your_output_dir # 输出目录，该目录的子目录是以id为名的，子目录中包含html脚本已经渲染好的png图片，以及manim.py文件

# 步骤4 视频渲染
- 脚本：5.render_manim_batch.py
- 需要修改的变量：
1. INPUT_ROOT = your_output_dir           # 步骤3得到的
2. OUTPUT_ROOT = your_video_output_dir    # 步骤4输出路径
```shell
python 5.render_manim_batch.py
```

# 步骤5 抽取并汇集视频
- 脚本：6.script_copy_mp4_files.py
- 需要修改的变量：
1. videos_dir = your_video_output_dir     # 步骤4得到的
2. OUTPUT_ROOT = your_all_video_output_dir    # 步骤5输出路径
```shell
python 6.script_copy_mp4_files.py
```

done!
