import os, PyQt5

dirname = os.path.dirname(PyQt5.__file__)
qt_dir = os.path.join(dirname, 'Qt5', 'plugins', 'platforms')
os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = qt_dir
import sys
import socket
import threading
import logging
from PyQt5.QtWidgets import QApplication, QMainWindow, QTextEdit, QVBoxLayout, QPushButton, QWidget, QHBoxLayout
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

# 自定义日志处理器，用于将日志信息发送到UI
class GUIHandler(logging.Handler):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent

    def emit(self, record):
        msg = self.format(record)
        self.parent.display_log_message.emit(msg)

class SensorServer(QObject):
    display_data = pyqtSignal(str)  # 定义信号用于在UI线程显示数据

    def __init__(self, host='0.0.0.0', port=12340):
        super(SensorServer, self).__init__()
        self.host = host
        self.port = port
        self.running = False
        self.clients = {}

    def start_listening(self):
        if self.running:
            logging.warning("服务器已在运行")
            return
        self.running = True
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind((self.host, self.port))
        self.socket.listen(5)
        logging.info("服务器监听 {}:{}".format(self.host, self.port))
        threading.Thread(target=self.accept_clients).start()

    def accept_clients(self):
        while self.running:
            try:
                client_socket, address = self.socket.accept()
                client_name = self.register_client(client_socket)
                logging.info("接受来自 {} as {}".format(address, client_name))
                threading.Thread(target=self.handle_client, args=(client_socket, client_name)).start()
            except Exception as e:
                logging.error("接受连接错误: {}".format(e))

    def register_client(self, client_socket):
        client_name = client_socket.recv(1024).decode().strip()  # 客户端在连接后立即发送其名称
        self.clients[client_socket] = client_name
        return client_name

    def handle_client(self, client_socket, client_name):
        try:
            while self.running:
                data = client_socket.recv(1024).decode()
                if not data:
                    break
                logging.debug(f"接受来自 {client_name}: {data}")
                if client_name and data:  # 确保客户端名存在且数据有效
                    self.display_data.emit(f"{client_name}: {data}")  # 发射信号更新UI，包含客户端标识
                if 'HEARTBEAT' in data:
                    client_socket.sendall(b'ACK')
        except Exception as e:
            logging.error(f"错误处理客户端 {client_name}: {e}")
        finally:
            client_socket.close()
            del self.clients[client_socket]
            logging.info(f"客户端 {client_name} 断开连接.")

    def stop_listening(self):
        self.running = False
        for client in self.clients.keys():
            client.close()
        self.socket.close()
        logging.info("服务停止.")

class Ui_MainWindow(QMainWindow):
    display_log_message = pyqtSignal(str)  # 新增信号用于传递日志信息到UI

    def __init__(self, server):
        super(Ui_MainWindow, self).__init__()
        self.server = server
        self.initUI()
        self.server.display_data.connect(self.update_ui)
        self.display_log_message.connect(self.log_to_ui)  # 连接新的信号到槽
        self.resize(800, 600)

    def initUI(self):
        self.setWindowTitle('传感器数据服务器')
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout()

        self.textEditLogs = QTextEdit()
        self.textEditLogs.setReadOnly(True)
        layout.addWidget(self.textEditLogs)

        self.textEditData = QTextEdit()
        self.textEditData.setReadOnly(True)
        layout.addWidget(self.textEditData)

        button_layout = QHBoxLayout()

        self.startButton = QPushButton('开始监听')
        self.startButton.clicked.connect(self.start_listening)
        button_layout.addWidget(self.startButton)

        self.stopButton = QPushButton('结束监听')
        self.stopButton.clicked.connect(self.stop_listening)
        button_layout.addWidget(self.stopButton)

        layout.addLayout(button_layout)

        central_widget.setLayout(layout)

    @pyqtSlot(str)
    def update_ui(self, data):
        self.textEditData.append(data)

    def log_to_ui(self, message):
        """将日志信息添加到UI的日志显示区域"""
        self.textEditLogs.append(message)

    def start_listening(self):
        self.server.start_listening()

    def stop_listening(self):
        self.server.stop_listening()

def setup_logging(ui):
    """设置日志系统，使用GUIHandler将日志信息发送到UI"""
    handler = GUIHandler(ui)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger = logging.getLogger()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

if __name__ == '__main__':
    try:
        app = QApplication(sys.argv)
        server = SensorServer()
        ui = Ui_MainWindow(server)
        setup_logging(ui)  # 设置日志处理
        ui.show()
        sys.exit(app.exec_())
    except KeyboardInterrupt:
        print("\n服务器关闭.")
        if hasattr(ui, 'server') and ui.server:
            ui.server.stop_listening()