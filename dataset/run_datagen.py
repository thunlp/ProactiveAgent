import glob
import os
import sys
import subprocess
from concurrent.futures import ThreadPoolExecutor,as_completed



def run(cfg_file_path,out_file_path):
    if os.environ.get("SETUP_PROACTIVE_AGENT","True") == "True":
        ps = subprocess.run(
            ["python","-m","gym.main","--cfg_file",cfg_file_path,"--out_file",out_file_path],
            stderr=sys.stderr,stdout=sys.stdout,env=os.environ,
            )
    else:
        ps = subprocess.run(
            ["python","-m","gym.main","--cfg_file",cfg_file_path,"--out_file",out_file_path.replace(".jsonl","_noagent.jsonl")],
            stderr=sys.stderr,stdout=sys.stdout,env=os.environ,
            )
    ps.check_returncode()
    return

if __name__ == "__main__":

    save_path = "dataset/agent_data"

    cfg_files = glob.glob(os.path.join(save_path,"*.yaml"))
    cfg_files.sort(key = lambda x: int(x.split("_")[-1].split(".")[0]))
    with ThreadPoolExecutor(max_workers=4) as pool:
        tasks = []
        for file in cfg_files:

            tasks.append(
                pool.submit(run,file,file.replace(".yaml",".jsonl"))
            )

        for task in as_completed(tasks):
            try:
                task.result()
            except Exception as e:
                print(e)
                continue