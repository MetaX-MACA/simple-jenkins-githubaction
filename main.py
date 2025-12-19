#!/usr/bin/env python3
# -*- coding:utf-8 -*-


import json
import logging
import os
from api4jenkins import Jenkins
from time import time, sleep


log_level = os.environ.get("INPUT_LOG_LEVEL", "INFO")
logging.basicConfig(format="JENKINS_ACTION: %(message)s", level=log_level)

logging.getLogger('httpx').setLevel(logging.WARNING)

def main():
    # jenkins info
    url = os.environ.get("INPUT_URL")
    job_name = os.environ["INPUT_JOB_NAME"]
    username = os.environ["INPUT_USERNAME"]
    api_token = os.environ["INPUT_API_TOKEN"]

    # connection settings
    cookies = os.environ.get("INPUT_COOKIES")
    timeout = int(os.environ.get("INPUT_TIMEOUT"))
    start_timeout = int(os.environ.get("INPUT_START_TIMEOUT"))
    interval = int(os.environ.get("INPUT_INTERVAL"))

    # pull request info
    pr_num = os.environ.get("INPUT_PR_NUMBER")
    project_branch = os.environ["INPUT_PROJECT_BRANCH"]

    if cookies:
        try:
            cookies = json.loads(cookies)
        except json.JSONDecodeError as e:
            raise Exception("`cookies` is not valid JSON.") from e
    else:
        cookies = {}

    jenkins = Jenkins(url, auth=(username, api_token), cookies=cookies)

    try:
        jenkins.version
    except Exception as e:
        raise Exception("Could not connect to Jenkins.") from e

    logging.info("Successfully connected to Jenkins.")

    parameters = {"pr_number": pr_num, "branch": project_branch}

    queue_item = jenkins.build_job(job_name, **parameters)
    logging.info("Start to start jenkins job")

    t0 = time()
    sleep(interval)
    while time() - t0 < start_timeout:
        build = queue_item.get_build()
        if build:
            break
        logging.info(f"Waiting for starting jenkins job. Waiting {interval} seconds.")
        sleep(interval)
    else:
        raise Exception(
            f"Timeout to start jenkins job. Waited for {start_timeout} seconds."
        )

    job_console = f"{build.url}console"
    logging.info(f"jenkins job url:{job_console}")
    
    t1 = time()
    sleep(interval)
    while time() - t1 < timeout:
        result = build.result
        if result == "SUCCESS":
            logging.info("Build successful 🎉")
            with open(os.environ["GITHUB_OUTPUT"], "a") as fh:
                print(f"log_url={job_console}", file=fh)
            print(f"::notice title=log_url::{job_console}")
            return
        elif result in ("FAILURE", "ABORTED", "UNSTABLE"):
            raise Exception(f'Build status returned "{result}". Build has failed ☹️.')
        sleep(interval)
    else:
        raise Exception(
            f"Build has not finished and timed out. Waited for {timeout} seconds."
        )


if __name__ == "__main__":
    main()
