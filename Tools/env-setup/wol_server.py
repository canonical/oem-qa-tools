#!/usr/bin/python3

import logging
import threading
import time
import subprocess
import shlex
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

app = FastAPI()

LOG_LEVEL = "DEBUG"
logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger(__name__)


@app.post("/")
async def testing(wol_request: dict):
    try:
        ret_server = tasker_main(wol_request)
        return ret_server
    except Exception as e:
        logger.critical(repr(e))


def send_wol_command(wol_info: dict):

    dut_mac = wol_info["DUT_MAC"]
    dut_ip = wol_info["DUT_IP"]
    wake_type = wol_info["wake_type"]

    command_dict = {
        "g": "wakeonlan -i {} {}".format(dut_ip, dut_mac),
        "a": "ping {}".format(dut_ip),
    }
    try:
        logger.debug("Wake on lan command: {}".format(command_dict[wake_type]))
        output = subprocess.check_output(shlex.split(command_dict[wake_type]))
        logger.debug({output})

    except subprocess.CalledProcessError as e:
        logger.error("Error occurred in tasker_main: {}".format(e))
        return False

    except KeyError as e:
        logger.error("Error occurred in tasker_main: {}".format(e))
        return False

    return True


def tasker_main(request: dict) -> dict:

    try:
        # Extracting necessary fields from the request
        dut_ip = request.get("DUT_IP")
        delay = request.get("delay")

        if not dut_ip or delay is None:
            logger.error("Missing required fields: DUT_IP or delay")
            return JSONResponse(
                content=jsonable_encoder(
                    {"message": "Missing required fields"}
                ),
                status_code=400,
            )

        logger.info("Received request: {}".format(request))
        logger.info("DUT_IP: {}".format(dut_ip))

        # Starting the task in a separate thread
        thread = threading.Thread(target=run_task, args=(request, delay))
        thread.start()

        # Returning success response
        return JSONResponse(
            content=jsonable_encoder({"message": "success"}), status_code=200
        )

    except Exception as e:
        logger.exception(
            "Error occurred while processing the request: {}".format(e)
        )
        return JSONResponse(
            content=jsonable_encoder({"message": str(e)}), status_code=500
        )


def is_pingable(ip_address):
    try:
        # use ping command to ping the host
        command = ["ping", "-c", "1", "-W", "1", ip_address]
        output = subprocess.check_output(
            command, stderr=subprocess.STDOUT, universal_newlines=True
        )
        logger.debug("ping: {}".format(output))
        return True
    except subprocess.CalledProcessError as e:
        logger.debug("An error occurred while ping the DUT: str{}".format(e))
        return False


def run_task(data, delay):

    dut_ip = data["DUT_IP"]
    delay = data["delay"]
    retry_times = data["retry_times"]

    for attempt in range(retry_times):
        # logger.info("threading:", dut_mac)
        logger.debug("retry times: {}".format(attempt))
        time.sleep(delay)

        try:
            # send wol command to the dut_mac
            logger.debug("send wol command to the dut_mac")
            send_wol_command(data)

            # delay a little time, ping the DUT,
            # if not up, send wol command again
            logger.debug("ping DUT to see if it had been waked up")
            time.sleep(delay)
            # ping dut
            if is_pingable(dut_ip):
                logger.info("{} is pingable, the DUT is back".format(dut_ip))
                return True
            else:
                logger.info(
                    "{} is NOT pingable, the DUT is not back.".format(dut_ip)
                )

        except Exception as e:
            logger.error("Error occurred in tasker_main: {}".format(e))

    return False
