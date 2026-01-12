import json 


offline_data_formate_data_path = "/data/temp_yhzou6/数学图形化讲解/files_yhzou/data/ori_data/立体图形/立体图形的周长、面积、表面积、体积（容积）的计算.json"
output_path = offline_data_formate_data_path.replace(".json", "_source_data.json")


def main():
    fw = open(output_path, 'w', encoding='utf-8')
    with open(offline_data_formate_data_path, 'r', encoding='utf-8') as fr:
        _data = {}
        for line in fr:
            json_line = json.loads(line)
            _data['id'] = json_line['topic_id']
            _data['input'] = {
                'content': json_line['video_content'],
                'analyse': {
                    'explainContent': json_line['video_analyse']['explainContent'],
                    'displayContent': json_line['video_analyse']['displayContent']
                }
            }
            fw.write(json.dumps(_data, ensure_ascii=False) + '\n')




if __name__ == "__main__":
    main()