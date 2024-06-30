import os, PyQt5

dirname = os.path.dirname(PyQt5.__file__)
qt_dir = os.path.join(dirname, 'Qt5', 'plugins', 'platforms')
os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = qt_dir
from PyQt5 import QtWidgets
import socket
import threading
import random
import time
import sys
class SensorClientGUI2(QtWidgets.QMainWindow):
    def __init__(self, server_ip='localhost', server_port=12340):
        super().__init__()
        self.server_ip = server_ip
        self.server_port = server_port
        self.client_socket = None
        self.heartbeat_thread = None
        self.running = True
        self.generated_data = ""

        self.initUI()

    def initUI(self):
        self.setWindowTitle('传感器数据客户端 2')
        central_widget = QtWidgets.QWidget(self)
        self.setCentralWidget(central_widget)
        self.resize(600, 375)

        layout = QtWidgets.QVBoxLayout()

        self.data_display = QtWidgets.QTextEdit()
        self.data_display.setReadOnly(True)
        layout.addWidget(self.data_display)

        button_layout = QtWidgets.QHBoxLayout()

        self.connect_button = QtWidgets.QPushButton('连接')
        self.connect_button.clicked.connect(self.connect_to_server)
        button_layout.addWidget(self.connect_button)

        self.disconnect_button = QtWidgets.QPushButton('断开连接')
        self.disconnect_button.clicked.connect(self.disconnect_from_server)
        self.disconnect_button.setEnabled(False)
        button_layout.addWidget(self.disconnect_button)

        self.generate_button = QtWidgets.QPushButton('产生数据')
        self.generate_button.clicked.connect(self.generate_and_show_data)
        button_layout.addWidget(self.generate_button)

        self.send_data_button = QtWidgets.QPushButton('发送数据')
        self.send_data_button.clicked.connect(self.send_generated_data)
        self.send_data_button.setEnabled(False)
        button_layout.addWidget(self.send_data_button)

        layout.addLayout(button_layout)

        self.status_label = QtWidgets.QLabel('断开连接')
        layout.addWidget(self.status_label)

        central_widget.setLayout(layout)

        self.show()

    def connect_to_server(self):
        if self.client_socket:
            return
        self.connect_button.setEnabled(False)
        self.disconnect_button.setEnabled(True)
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.client_socket.connect((self.server_ip, self.server_port))
            self.client_socket.sendall(b'CLIENT2')  # 发送客户端标识给服务器
            self.status_label.setText(f'连接到 {self.server_ip}:{self.server_port}')
            self.start_heartbeat()
        except Exception as e:
            self.status_label.setText(f"连接失败:  {e}")
            self.disconnect_from_server()

    def generate_and_show_data(self):
        self.generated_data = self.generate_random_data()
        self.data_display.append(f"产生:  {self.generated_data}")
        self.send_data_button.setEnabled(True)
        self.generated_data = f"客户端-2{self.generated_data}"  # 包含客户端标识符

    def send_generated_data(self):
        if self.client_socket and self.generated_data:
            try:
                self.client_socket.sendall(self.generated_data.encode())
                self.data_display.append(f"发送: {self.generated_data}")
                self.generated_data = ""
                self.send_data_button.setEnabled(False)
            except Exception as e:
                self.data_display.append(f"数据发送失败:{str(e)}")

    def disconnect_from_server(self):
        self.running = False
        self.connect_button.setEnabled(True)
        self.disconnect_button.setEnabled(False)

        # 停止心跳线程
        if self.heartbeat_thread and self.heartbeat_thread.is_alive():
            self.heartbeat_thread.join()
        self.heartbeat_thread = None

        # 关闭套接字，加入异常处理
        if self.client_socket:
            try:
                self.client_socket.shutdown(socket.SHUT_RDWR)
                self.client_socket.close()
            except OSError as e:
                self.data_display.append(f"断开连接时出现错误: {str(e)}")
            finally:
                self.client_socket = None

        self.status_label.setText("断开连接")
        self.send_data_button.setEnabled(False)

    def start_heartbeat(self):
        threading.Thread(target=self.send_heartbeat, daemon=True).start()

    def send_heartbeat(self):
        while self.running:
            try:
                self.client_socket.sendall(b'HEARTBEAT')
                time.sleep(5)
            except socket.error as e:
                self.status_label.setText(f"由于错误导致心跳停止{e}")
                self.disconnect_from_server()

    def generate_random_data(self):
        temperature = random.randint(-10, 50)
        humidity = random.randint(0, 100)
        return f"温度:{temperature}, 湿度:{humidity}"


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = SensorClientGUI2()
    sys.exit(app.exec_())