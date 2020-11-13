#!/usr/bin/env python3

# Copyright (c) Facebook, Inc. and its affiliates.
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import os
import shutil
import subprocess
from mephisto.operations.operator import Operator
from mephisto.operations.utils import get_root_dir
from mephisto.tools.scripts import load_db_and_process_config
from mephisto.data_model.assignment import InitializationData
from mephisto.abstractions.blueprints.static_react_task.static_react_blueprint import (
    BLUEPRINT_TYPE,
)
from mephisto.abstractions.blueprints.abstract.static_task.static_blueprint import (
    SharedStaticTaskState,
)

import hydra
from omegaconf import DictConfig
from dataclasses import dataclass, field
from typing import List, Any
import time
import random

TASK_DIRECTORY = os.path.dirname(os.path.abspath(__file__))

defaults = [
    {"mephisto/blueprint": BLUEPRINT_TYPE},
    {"mephisto/architect": "local"},
    {"mephisto/provider": "mock"},
    {"conf": "example"},
]

from mephisto.operations.hydra_config import RunScriptConfig, register_script_config


@dataclass
class TestScriptConfig(RunScriptConfig):
    defaults: List[Any] = field(default_factory=lambda: defaults)
    task_dir: str = TASK_DIRECTORY
    video_source_dir: str = os.path.join(TASK_DIRECTORY, "videos")


register_script_config(name="scriptconfig", module=TestScriptConfig)


# TODO it would be nice if this was automated in the way that it
# is for ParlAI custom frontend tasks
def build_task(task_dir):
    """Rebuild the frontend for this task"""

    frontend_source_dir = os.path.join(task_dir, "webapp")
    frontend_build_dir = os.path.join(frontend_source_dir, "build")

    return_dir = os.getcwd()
    os.chdir(frontend_source_dir)
    if os.path.exists(frontend_build_dir):
        shutil.rmtree(frontend_build_dir)
    packages_installed = subprocess.call(["npm", "install"])
    if packages_installed != 0:
        raise Exception(
            "please make sure npm is installed, otherwise view "
            "the above error for more info."
        )

    webpack_complete = subprocess.call(["npm", "run", "dev"])
    if webpack_complete != 0:
        raise Exception(
            "Webpack appears to have failed to build your "
            "frontend. See the above error for more information."
        )
    os.chdir(return_dir)


@hydra.main(config_name="scriptconfig")
def main(cfg: DictConfig) -> None:
    task_dir = cfg.task_dir

    video_dir = cfg.video_source_dir

    video_files = os.listdir(video_dir)
    compatible_video_files = [
        f for f in video_files if f.split(".")[-1] in ["mov", "mp4"]
    ]

    static_task_data = [
        {
            "video": v,
            "model_annotations": [],
        }
        for v in compatible_video_files
    ]

    def get_task_data():
        random.shuffle(static_task_data)
        for n in static_task_data:
            print("***** Ranking candidates to be annotated")
            print("***** Annotating with new model")
            start_time = random.randint(0, 30)
            end_time = random.randint(start_time + 5, start_time + 40)
            n["model_annotations"] = [
                {
                    "start_time": start_time,
                    "end_time": end_time,
                    "label": "In a living room, two friends make coffee and sit on a couch.  #Summary",
                }
            ]
            yield InitializationData(shared=n, unit_data=[{}])
            input("***** Waiting for data......\n")
            print("***** Training new model.........")
            time.sleep(2)
        return False

    shared_state = SharedStaticTaskState(
        static_task_data=get_task_data(),
    )

    build_task(task_dir)

    db, cfg = load_db_and_process_config(cfg)
    operator = Operator(db)

    operator.validate_and_run_config(cfg.mephisto, shared_state)
    operator.wait_for_runs_then_shutdown(skip_input=True, log_rate=30)


if __name__ == "__main__":
    main()
