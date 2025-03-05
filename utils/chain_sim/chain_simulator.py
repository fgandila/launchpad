import stat
from venv import logger


from config import *
import os
import signal
import subprocess
from subprocess import Popen
from threading import Thread
import threading
from utils.chain_sim.constants import *

class ChainSimulator:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.log_level = log_level
        self.num_validators_per_shard = num_validators_per_shard
        self.num_validators_meta = num_validators_meta
        self.num_waiting_validators_per_shard = num_waiting_validators_per_shard
        self.num_waiting_validators_meta = num_waiting_validators_meta
        self.rounds_per_epoch = rounds_per_epoch
        self.process = None

    def start(self):
        command = f"./chainsimulator --log-level {self.log_level} --rounds-per-epoch {rounds_per_epoch}\
                                    -num-validators-per-shard {self.num_validators_per_shard} \
                                    -num-waiting-validators-per-shard {num_waiting_validators_per_shard} \
                                    -num-validators-meta {num_validators_meta} \
                                    -num-waiting-validators-meta {num_waiting_validators_meta}"
        command = ' '.join(command.split())

        flag = True
        while flag:
            if "  " in command:
                command = command.replace("  ", " ")
            else:
                flag = False
        logger.info(f"Starting ChainSimulator with command: {command}")

        self.process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                        shell=True, preexec_fn=os.setsid, cwd=chain_simulator_path)

        stdout_thread = threading.Thread(
            target=self.read_output, args=(self.process.stdout,))
        stderr_thread = threading.Thread(
            target=self.read_output, args=(self.process.stderr, True))
        stdout_thread.start()
        stderr_thread.start()
        
    def read_output(self, stream, is_error=False):
        """Reads from a stream and logs the output."""
        try:
            for line in iter(stream.readline, b''):
                line.decode()
                # TODO Use the code below in order to retreive the chain Simulator logs
                # if is_error:
                #     logger.error(decoded_line.strip())
                # else:
                #     logger.info(decoded_line.strip())
        finally:
            stream.close()

    def stop(self):
        if self.process is not None:
            # Send SIGTERM to the process group to cleanly stop all processes
            os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)

            self.process.wait()

            # Ensure output threads are also terminated
            if hasattr(self, 'stdout_thread'):
                self.stdout_thread.join()
            if hasattr(self, 'stderr_thread'):
                self.stderr_thread.join()

            logger.info(
                "ChainSimulator process and all child processes stopped\n")
        else:
            logger.warning("\nNo ChainSimulator process found.\n")
