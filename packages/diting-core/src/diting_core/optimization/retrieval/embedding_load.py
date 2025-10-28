import json


def read_json_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
            return data
    except FileNotFoundError:
        print(f"错误：文件 {file_path} 未找到。")
        return None
    except json.JSONDecodeError as e:
        print(f"错误：JSON 解码失败 - {e}")
        return None
    except Exception as e:
        print(f"发生未知错误：{e}")
        return None


# 使用示例
if __name__ == "__main__":
    # 替换为你的 JSON 文件路径
    file_path = r'D:\diting\packages\diting-core\src\diting_core\optimization\datasets\retrieval_data\embeddings_cache.json'
    # file_path = r'D:\diting\packages\diting-core\src\diting_core\optimization\datasets\retrieval_data\embeddings_cache - 副本.json'

    json_data = read_json_file(file_path)
    print(len(json_data))

    if json_data is not None:
        print("读取到的数据：")
        print(json.dumps(json_data, indent=4, ensure_ascii=False))