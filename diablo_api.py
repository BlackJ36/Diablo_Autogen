import socket
import openai
from time import sleep



# define data transsmission betwenn 1.BCI and local 2. local and ChatGPt 3. local and diablo
class diablo:

    def __init__(self,local_add='', port='', robot_add='10', rport='8848'):
        self._local_add = local_add
        self._port = int(port)
        self._udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._message = ''
        self._robot_add = robot_add
        self._rport = int(rport)
        self._remote_addr = (self._robot_add, self._rport)
        self.setup_socket()

    def setup_socket(self):
        # local_addr = ('127.0.0.1', 8801)
        local_addr = (self._local_add, self._port)
        self._udp.bind(local_addr)
        print(f'UDP will receive from {self._local_add}: {self._port}')

    def wait_for_bci(self):
        data_list = ''
        print("UDP is listening from BCI decoder")

        while True:
            data, _ = self._udp.recvfrom(24)
            data = data.decode()  # 获取信息
            print(f"got command :{data.strip()}")
            self._message = self._message + data
            data_list = self._message
            if data == '`' or len(self._message) == 11:
                break
        self._message = ''
        return data_list

    def send_robot_command(self, command):
        # self._udp.sendto(command.encode(), self._remote_addr)
        print(command)
        print("OK!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print('\n')

    def get_IMU(self):
        # todo:get imu sessage as {pitch:'',roll:'',yaw:''}
        # print(f"imu_message: {}")
        pass
        return {"pitch": 0.00, "roll": 0.00, "yaw": 0.00}

    def __del__(self):
        self._udp.close()
        print("销毁对象{0}".format(self))


# if __name__ == "__main__":
#     trans = Transmission(openai_api_key='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',
#                          local_add="127.0.0.1", port=8801)
