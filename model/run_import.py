import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# 统一的ChromaDB持久化目录
UNIFIED_PERSIST_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'chroma_db_unified')

# 所有主题的配置
topics_config = [
    {
        'collection_name': 'MSVaccination',
        'docs_dir': os.path.join('Data', 'documents', 'MSVaccination'),
        'chunk_size': 1000,
        'overlap': 200,
        'batch_size': 500
    },
    {
        'collection_name': 'DiabeticPolyneuropathy',
        'docs_dir': os.path.join('Data', 'documents', 'DiabeticPolyneuropathy'),
        'chunk_size': 1000,
        'overlap': 200,
        'batch_size': 500
    },
    {
        'collection_name': 'TT_book1',
        'docs_dir': os.path.join('Data', 'documents', 'TT_book1'),
        'chunk_size': 1000,
        'overlap': 200,
        'batch_size': 500
    },
    {
        'collection_name': 'TT_book2',
        'docs_dir': os.path.join('Data', 'documents', 'TT_book2'),
        'chunk_size': 1000,
        'overlap': 200,
        'batch_size': 500
    },
    {
        'collection_name': 'TT_book4',
        'docs_dir': os.path.join('Data', 'documents', 'TT_book4'),
        'chunk_size': 1000,
        'overlap': 200,
        'batch_size': 500
    },
    {
        'collection_name': 'AntiseizureWithdrawal',
        'docs_dir': os.path.join('Data', 'documents', 'AntiseizureWithdrawal'),
        'chunk_size': 1000,
        'overlap': 200,
        'batch_size': 500
    },
    {
        'collection_name': 'Borreliosis',
        'docs_dir': os.path.join('Data', 'documents', 'Borreliosis'),
        'chunk_size': 1000,
        'overlap': 200,
        'batch_size': 500
    },
    {
        'collection_name': 'BrainDeath',
        'docs_dir': os.path.join('Data', 'documents', 'BrainDeath'),
        'chunk_size': 1000,
        'overlap': 200,
        'batch_size': 500
    },
    {
        'collection_name': 'DopaminergicEarlyParkinson',
        'docs_dir': os.path.join('Data', 'documents', 'DopaminergicEarlyParkinson'),
        'chunk_size': 1000,
        'overlap': 200,
        'batch_size': 500
    },
    {
        'collection_name': 'EpilepsyInWOCBP',
        'docs_dir': os.path.join('Data', 'documents', 'EpilepsyInWOCBP'),
        'chunk_size': 1000,
        'overlap': 200,
        'batch_size': 500
    },
    {
        'collection_name': 'MigraineInChildren',
        'docs_dir': os.path.join('Data', 'documents', 'MigraineInChildren'),
        'chunk_size': 1000,
        'overlap': 200,
        'batch_size': 500
    },
    {
        'collection_name': 'MigrainePreventionInChildren',
        'docs_dir': os.path.join('Data', 'documents', 'MigrainePreventionInChildren'),
        'chunk_size': 1000,
        'overlap': 200,
        'batch_size': 500
    },
    {
        'collection_name': 'SleepAutism',
        'docs_dir': os.path.join('Data', 'documents', 'SleepAutism'),
        'chunk_size': 1000,
        'overlap': 200,
        'batch_size': 500
    },
    {
        'collection_name': 'StrokeForamenOvale',
        'docs_dir': os.path.join('Data', 'documents', 'StrokeForamenOvale'),
        'chunk_size': 1000,
        'overlap': 200,
        'batch_size': 500
    },
    {
        'collection_name': 'StrokeInLargeVessel',
        'docs_dir': os.path.join('Data', 'documents', 'StrokeInLargeVessel'),
        'chunk_size': 1000,
        'overlap': 200,
        'batch_size': 500
    },
    {
        'collection_name': 'TicDisorders',
        'docs_dir': os.path.join('Data', 'documents', 'TicDisorders'),
        'chunk_size': 1000,
        'overlap': 200,
        'batch_size': 500
    }
]

# 创建统一的ChromaDB目录
os.makedirs(UNIFIED_PERSIST_DIR, exist_ok=True)

# 记录导入结果
import_results = []


def run_vector_maker(topic_config):
    """运行vectorMaker.py脚本导入单个主题的数据"""
    collection_name = topic_config['collection_name']
    docs_dir_relative = topic_config['docs_dir']
    chunk_size = topic_config['chunk_size']
    overlap = topic_config['overlap']
    batch_size = topic_config['batch_size']

    # 构造绝对路径
    base_dir = os.path.dirname(os.path.abspath(__file__))
    full_docs_dir = os.path.join(base_dir, docs_dir_relative)

    # 检查文档目录是否存在
    if not os.path.exists(full_docs_dir):
        return {
            'collection_name': collection_name,
            'status': 'failed',
            'error': f'文档目录不存在: {full_docs_dir}'
        }

    # 设置环境变量 - 确保变量名与 vectorMaker.py 中的一致
    env = os.environ.copy()
    env['PYTHONIOENCODING'] = 'utf-8'
    env['PYTHONUTF8'] = '1'
    env['ANTISEIZURE_DOCS_DIR'] = full_docs_dir
    env['CHROMA_PERSIST_DIR'] = UNIFIED_PERSIST_DIR
    env['CHROMA_COLLECTION_NAME'] = collection_name
    env['CHUNK_SIZE'] = str(chunk_size)
    env['OVERLAP'] = str(overlap)
    env['BATCH_SIZE'] = str(batch_size)

    start_time = time.time()
    print(f"\n开始导入主题: {collection_name}")
    print(f"文档目录: {full_docs_dir}")
    print(f"ChromaDB目录: {UNIFIED_PERSIST_DIR}")
    print(f"分块大小: {chunk_size}, 重叠大小: {overlap}, 批量大小: {batch_size}")

    try:
        # 运行vectorMaker.py脚本
        result = subprocess.run(
            [sys.executable, os.path.join(base_dir, 'vectorMaker.py')],
            env=env,
            capture_output=True,
            text=True,
            encoding='utf-8',
            check=True
        )

        elapsed_time = time.time() - start_time
        print(f"主题 {collection_name} 导入成功! 耗时: {elapsed_time:.2f} 秒")

        # 解析输出，获取导入的文档数量和块数量
        documents_count = 0
        chunks_count = 0

        stdout = result.stdout
        stderr = result.stderr

        if stdout:
            for line in stdout.split('\n'):
                if '发现' in line and '个 PDF 文件' in line:
                    try:
                        documents_count = int(line.split('发现')[1].split('个 PDF 文件')[0].strip())
                    except:
                        pass
                elif '待 upsert 的总 chunks 数量' in line:
                    try:
                        chunks_count = int(line.split('：')[1].strip())
                    except:
                        pass

        return {
            'collection_name': collection_name,
            'status': 'success',
            'documents_count': documents_count,
            'chunks_count': chunks_count,
            'elapsed_time': elapsed_time,
            'stdout': stdout,
            'stderr': stderr
        }

    except subprocess.CalledProcessError as e:
        elapsed_time = time.time() - start_time
        stdout = e.stdout
        stderr = e.stderr
        error_message = f"子进程执行失败，返回码: {e.returncode}\n" \
                        f"标准输出: {stdout}\n" \
                        f"标准错误: {stderr}"
        print(f"主题 {collection_name} 导入失败! 耗时: {elapsed_time:.2f} 秒")
        print(f"错误: {error_message}")

        return {
            'collection_name': collection_name,
            'status': 'failed',
            'error': error_message,
            'elapsed_time': elapsed_time
        }
    except Exception as e:
        elapsed_time = time.time() - start_time
        error_message = str(e)
        print(f"主题 {collection_name} 导入时发生未知错误! 耗时: {elapsed_time:.2f} 秒")
        print(f"错误: {error_message}")

        return {
            'collection_name': collection_name,
            'status': 'failed',
            'error': error_message,
            'elapsed_time': elapsed_time
        }


def main():
    """主函数，遍历所有主题并导入数据"""
    print("=" * 80)
    print(f"开始批量导入医学RAG数据 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"统一ChromaDB持久化目录: {UNIFIED_PERSIST_DIR}")
    print(f"共需导入 {len(topics_config)} 个主题")
    print("=" * 80)

    start_total_time = time.time()

    for topic_config in topics_config:
        result = run_vector_maker(topic_config)
        import_results.append(result)

    total_time = time.time() - start_total_time

    # 生成导入结果摘要
    print("\n" + "=" * 80)
    print(f"批量导入完成 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"总耗时: {total_time:.2f} 秒")
    print("=" * 80)

    success_count = sum(1 for r in import_results if r['status'] == 'success')
    failed_count = len(import_results) - success_count

    print(f"导入结果统计:")
    print(f"  成功: {success_count} 个主题")
    print(f"  失败: {failed_count} 个主题")

    if success_count > 0:
        print("\n成功导入的主题详情:")
        for result in import_results:
            if result['status'] == 'success':
                print(f"  - {result['collection_name']}:")
                print(f"    文档数量: {result['documents_count']}")
                print(f"    块数量: {result['chunks_count']}")
                print(f"    耗时: {result['elapsed_time']:.2f} 秒")

    if failed_count > 0:
        print("\n导入失败的主题详情:")
        for result in import_results:
            if result['status'] == 'failed':
                print(f"  - {result['collection_name']}:")
                print(f"    错误: {result['error'][:200]}..." if len(
                    result['error']) > 200 else f"    错误: {result['error']}")

    print("=" * 80)


if __name__ == "__main__":
    main()