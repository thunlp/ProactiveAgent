import json
import os
import uuid
import time
import gradio as gr
import random

current_dir = os.path.dirname(os.path.abspath(__file__))

data_dir = os.path.join(current_dir, "data")
save_dir = os.path.join(current_dir, "result")
id_data_map_file = os.path.join(current_dir, "uuid_data-index_map.json")
name_id_map_file = os.path.join(current_dir, "name_id_map.json")

TASK_NUM = 5
HOST = "127.0.0.1"
PORT = 8000

ALL_TRACE_DOWN = "All traces done!!!"
CONTINUE_TO_BEGIN = "Press [Continue] to begin the new trace"
PRESS_NEXT_TRACE = "Current trace done. Press [next trace]!!!"

TASK_CHECK = [f"Task {i+1}" for i in range(TASK_NUM)]
NEED_HLLP_CHECK = ["Help needed", "No help needed"]


def same_auth(username, password):
    return str(password) == "password"


def read_json(file_path):
    while True:
        try:
            # 尝试获取锁（创建一个临时文件作为锁）
            lock_file = file_path + ".lock"
            with open(lock_file, "x"):
                break
        except FileExistsError:
            # 如果锁文件已存在，说明文件正在被其他进程使用，等待一段时间后重试
            # print("文件被占用，稍候再试...")
            time.sleep(1)

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = json.load(f)
            # print("读取内容:", content)
    finally:
        # 无论读取是否成功，都记得删除锁文件
        os.remove(lock_file)
    return content


def write_json(file_path, content):
    while True:
        try:
            lock_file = file_path + ".lock"
            with open(lock_file, "x"):
                break
        except FileExistsError:
            # print("文件被占用，稍候再试...")
            time.sleep(1)

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(content, f, ensure_ascii=False, indent=4)
            # print("写入成功")
    finally:
        # 删除锁文件
        os.remove(lock_file)


def get_id(request: gr.Request):
    if not os.path.exists(name_id_map_file):
        write_json(name_id_map_file, {})
    name_id_map = read_json(name_id_map_file)
    user_uuid = name_id_map.get(request.username)
    if user_uuid is None:
        user_uuid = str(uuid.uuid4().hex)
        name_id_map[request.username] = user_uuid
        write_json(name_id_map_file, name_id_map)
    return user_uuid


def task_handle(data):
    tasks = data["agent_response"]["candidate_task"]
    if len(tasks) < TASK_NUM:
        tasks += ["None"] * (TASK_NUM - len(tasks))
    return tasks


def update_user_data(user_id, trace_name):
    """更新id和数据索引的映射关系"""
    id_data_idx_map = read_json(id_data_map_file)
    if user_id not in id_data_idx_map.keys():
        id_data_idx_map[user_id] = []
    id_data_idx_map[user_id].append(trace_name)
    write_json(id_data_map_file, id_data_idx_map)


def next_trace(user_id, trace_name, obs):
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    if not os.path.exists(id_data_map_file):
        write_json(id_data_map_file, {})

    if isinstance(obs, list):
        return (
            obs,
            trace_name,
            0,
        )
    if isinstance(obs, dict) and "Status" in obs and obs["Status"] == CONTINUE_TO_BEGIN:
        return (
            {"Status": CONTINUE_TO_BEGIN},
            trace_name,
            0,
        )
    # 判断用户是否有未标注完的trace
    id_data_idx_map = read_json(id_data_map_file)
    if user_id in id_data_idx_map:
        user_data = id_data_idx_map[user_id]

        for tr_name in user_data:
            result = read_json(os.path.join(save_dir, f"{tr_name}.json"))
            data = read_json(os.path.join(data_dir, f"{tr_name}.json"))
            if len(result) < len(data):
                # print("xiaole")
                return (
                    {"Status": CONTINUE_TO_BEGIN},
                    tr_name,
                    len(result),
                )
            for i, item in enumerate(result):
                if "candidate_task" not in item:
                    continue
                if "" not in item["candidate_task"] and user_id not in item["real_user"]:
                    # print("shaole")
                    return (
                        {"Status": CONTINUE_TO_BEGIN},
                        tr_name,
                        i,
                    )
    # 读取data目录的文件, 根据对应结果文件判断是否需要标注
    for file in os.listdir(data_dir):
        tr_name = os.path.splitext(file)[0]
        if tr_name == "splits":
            continue
        result_path = os.path.join(save_dir, file)
        # 如果结果文件不存在，说明该trace还未标注
        if not os.path.exists(result_path):
            write_json(result_path, [])
            update_user_data(user_id, tr_name)
            return (
                {"Status": CONTINUE_TO_BEGIN},
                tr_name,
                0,
            )

        id_data_idx_map = read_json(id_data_map_file)
        # 如果当前用户未标注过该trace，且其他用户标注次数小于3次，则继续标注
        if (
            tr_name not in id_data_idx_map.get(user_id, [])
            and sum(tr_name in id_data_idx_map.get(uid, []) for uid in id_data_idx_map)
            < 3
        ):
            update_user_data(user_id, tr_name)
            return (
                {"Status": CONTINUE_TO_BEGIN},
                tr_name,
                0,
            )

    return (
        {"Status": ALL_TRACE_DOWN},
        trace_name,
        0,
    )


def judge_need_step(
    user_id, trace_name, history_obs, user_choice, user_reject, continue_id, turns
):
    id_choices = [3, 7, 10, 14]
    # 取第一个比长度大的数
    choice = 0
    for id in id_choices:
        if (
            id > max(len(history_obs) - 1, continue_id - 1)
            and "" in turns[id]["agent_response"]["candidate_task"]
        ):
            choice = id
            break
    save_result(
        user_id,
        trace_name,
        history_obs,
        user_choice,
        user_reject,
        turns,
        empty_judge=True,
    )
    if choice == 0:
        result = read_json(os.path.join(save_dir, f"{trace_name}.json"))
        result.extend(turns[len(result) :])
        write_json(os.path.join(save_dir, f"{trace_name}.json"), result)
        return {"Status": PRESS_NEXT_TRACE}, [],None,*(
            NEED_HLLP_CHECK + [None] * (TASK_NUM - len(NEED_HLLP_CHECK))
        )
    else:
        output_obs = history_obs.copy() if isinstance(history_obs, list) else []
        if output_obs == []:
            for i in range(continue_id):
                output_obs.append(turns[i]["observation"])
        for data in turns[len(output_obs) : choice + 1]:
            output_obs.append(data["observation"])

    return output_obs, [],None,*(NEED_HLLP_CHECK + [None] * (TASK_NUM - len(NEED_HLLP_CHECK)))


def step(user_id, trace_name, history_obs, user_choice, user_reject, continue_id=0):
    if not trace_name:
        return None, [], None,*([None] * TASK_NUM)

    if history_obs is None:
        history_obs = []
    elif (
        isinstance(history_obs, dict)
        and "Status" in history_obs
        and history_obs["Status"] != CONTINUE_TO_BEGIN
    ):
        return history_obs, [],None,*([None] * TASK_NUM)

    turns = read_json(os.path.join(data_dir, f"{trace_name}.json"))
    if "empty" in trace_name:
        return judge_need_step(
            user_id,
            trace_name,
            history_obs,
            user_choice,
            user_reject,
            continue_id,
            turns,
        )
    save_result(user_id, trace_name, history_obs, user_choice, user_reject, turns)

    tasks = ""
    # print(len(history_obs), len(turns))
    output_obs = history_obs.copy() if isinstance(history_obs, list) else []
    if output_obs == []:
        for i in range(continue_id):
            output_obs.append(turns[i]["observation"])
    # print("continue_id", continue_id)
    for data in turns[len(output_obs) :]:
        output_obs.append(data["observation"])
        if "" not in data["agent_response"]["candidate_task"]:
            tasks = task_handle(data)
            break

    if not tasks:
        result = read_json(os.path.join(save_dir, f"{trace_name}.json"))
        result.extend(turns[len(result) :])
        write_json(os.path.join(save_dir, f"{trace_name}.json"), result)
        return {"Status": PRESS_NEXT_TRACE}, [],None,*([None] * TASK_NUM)
    return output_obs,[],None, *tasks


def save_result(
    user_id, trace_name, history_obs, user_choice, user_reject, turns, empty_judge=False
):
    save_path = os.path.join(save_dir, f"{trace_name}.json")
    if history_obs and isinstance(history_obs, list):
        result_turns = read_json(save_path)
        for i in range(len(result_turns), len(history_obs)):
            for i in range(len(result_turns), len(history_obs)):
                result_turns.append(
                    {
                        "observation": turns[i]["observation"],
                        "candidate_task": turns[i]["agent_response"]["candidate_task"],
                    }
                )
        if "real_user" not in result_turns[len(history_obs) - 1]:
            result_turns[len(history_obs) - 1]["real_user"] = {}
        if empty_judge:
            result_choice = "need" if 0 in user_choice else "no need"

        else:
            if user_reject:
                result_choice = "Reject all"
            else:
                result_choice = sorted(user_choice)

        result_turns[len(history_obs) - 1]["real_user"][user_id] = result_choice

        write_json(save_path, result_turns)


demo = gr.Blocks(
    css=os.path.join(current_dir, "style.css"),
)

with demo:
    gr.Markdown("## User Response Annotation")
    continue_id = gr.Number(visible=False)
    with gr.Row():
        unique_uuid = gr.Textbox(
            label="Your UUID",
            interactive=False,
        )
        trace_name = gr.Text(label="current trace name", interactive=False)
    with gr.Row():
        observations = gr.Json(label="Observations", elem_id="scroll-box")
    with gr.Row():
        tasks = [gr.Textbox(label=f"Task {i+1}") for i in range(TASK_NUM)]
    with gr.Row():
        selected = gr.CheckboxGroup(
            TASK_CHECK, label="Choose the task you accept", type="index"
        )
    with gr.Row():
        reject_option = gr.Checkbox(label="Reject all")
    with gr.Row():
        submit = gr.Button(value="Continue")
        next_trace_btn = gr.Button(value="Next trace")

    submit.click(
        step,
        inputs=[
            unique_uuid,
            trace_name,
            observations,
            selected,
            reject_option,
            continue_id,
        ],
        outputs=[observations,selected,reject_option] + tasks,
    )
    next_trace_btn.click(
        next_trace,
        inputs=[unique_uuid, trace_name, observations],
        outputs=[observations, trace_name, continue_id],
    )
    demo.load(get_id, None, unique_uuid)


# data复制并重命名
# for file in os.listdir(data_dir):
#     if "empty" not in file:
#         data = read_json(os.path.join(data_dir, file))
#         write_json(os.path.join(data_dir, f"empty_{file}"), data)

demo.launch(auth=same_auth, share=False)
