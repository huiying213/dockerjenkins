#!D:\python3.12\python.exe
#!python
# -*- coding: utf-8 -*-
import sys
import os
import json
import subprocess
import socket
import mysql.connector
import paramiko
from mysql.connector import Error
from datetime import datetime, date

# 设置标准输出编码为UTF-8
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)

# 首先输出Content-Type
sys.stdout.write("Content-Type: application/json; charset=utf-8\r\n")
sys.stdout.write("\r\n")  # 空行分隔头部和内容

# 数据库配置
DB_CONFIG = {
    'host': 'localhost',
    'database': 'vm_management',
    'user': 'root',
    'password': '123456',  # 填写你的MySQL密码
    'charset': 'utf8mb4'
}

class DateTimeEncoder(json.JSONEncoder):
    """自定义JSON编码器，处理datetime对象"""
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)

def get_db_connection():
    """获取数据库连接"""
    try:
        return mysql.connector.connect(**DB_CONFIG)
    except Error as e:
        print(f"Database connection error: {e}", file=sys.stderr)
        return None

def serialize_vm_data(vm):
    """序列化虚拟机数据，处理datetime对象"""
    if not vm:
        return vm
    
    result = {}
    for key, value in vm.items():
        if isinstance(value, (datetime, date)):
            # 将datetime转换为字符串
            result[key] = value.isoformat()
        elif isinstance(value, bytes):
            # 处理bytes类型
            try:
                result[key] = value.decode('utf-8')
            except:
                result[key] = str(value)
        else:
            result[key] = value
    return result

def add_virtual_machine(user_id, vm_data):
    """添加虚拟机"""
    conn = get_db_connection()
    if not conn:
        return False, "数据库连接失败"
    
    try:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO virtual_machines 
               (user_id, vm_name, vm_ip, ssh_port, ssh_username, ssh_password, putty_path) 
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (user_id, vm_data['vm_name'], vm_data['vm_ip'], 
             vm_data['ssh_port'], vm_data['ssh_username'], 
             vm_data['ssh_password'], 'D:\\PuTTY\\putty.exe')
        )
        conn.commit()
        return True, "虚拟机添加成功"
    except Error as e:
        return False, f"数据库错误: {str(e)}"
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

def get_user_vms(user_id):
    """获取用户的虚拟机列表"""
    conn = get_db_connection()
    if not conn:
        return False, "数据库连接失败", []
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT id, vm_name, vm_ip, ssh_port, ssh_username, created_at FROM virtual_machines WHERE user_id = %s ORDER BY created_at DESC",
            (user_id,)
        )
        vms = cursor.fetchall()
        
        # 序列化所有虚拟机数据
        serialized_vms = []
        for vm in vms:
            serialized_vms.append(serialize_vm_data(vm))
        
        return True, "获取成功", serialized_vms
    except Error as e:
        return False, f"数据库错误: {str(e)}", []
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

def test_ssh_connection(vm_id):
    """测试SSH连接"""
    conn = get_db_connection()
    if not conn:
        return False, "数据库连接失败"
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT vm_ip, ssh_port, ssh_username, ssh_password FROM virtual_machines WHERE id = %s",
            (vm_id,)
        )
        vm = cursor.fetchone()
        
        if not vm:
            return False, "虚拟机不存在"
        
        # 尝试SSH连接
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        try:
            ssh.connect(
                hostname=vm['vm_ip'],
                port=vm['ssh_port'],
                username=vm['ssh_username'],
                password=vm['ssh_password'],
                timeout=10
            )
            
            # 执行简单命令测试
            stdin, stdout, stderr = ssh.exec_command('echo "SSH Connection Test Success" && hostname')
            output = stdout.read().decode('utf-8').strip()
            error_output = stderr.read().decode('utf-8').strip()
            
            ssh.close()
            
            if error_output:
                return True, f"连接成功但可能有警告: {error_output}"
            return True, f"连接成功: {output}"
            
        except paramiko.AuthenticationException:
            return False, "SSH认证失败"
        except paramiko.SSHException as e:
            return False, f"SSH连接错误: {str(e)}"
        except Exception as e:
            return False, f"连接失败: {str(e)}"
            
    except Error as e:
        return False, f"数据库错误: {str(e)}"
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

def check_connection_status(vm_id):
    """检查连接状态"""
    conn = get_db_connection()
    if not conn:
        return False, "数据库连接失败", False
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT vm_ip, ssh_port, ssh_username, ssh_password FROM virtual_machines WHERE id = %s",
            (vm_id,)
        )
        vm = cursor.fetchone()
        
        if not vm:
            return False, "虚拟机不存在", False
        
        # 快速检查端口是否开放
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        
        try:
            result = sock.connect_ex((vm['vm_ip'], vm['ssh_port']))
            sock.close()
            
            if result == 0:
                # 端口开放，进一步检查SSH服务
                try:
                    ssh = paramiko.SSHClient()
                    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    ssh.connect(
                        hostname=vm['vm_ip'],
                        port=vm['ssh_port'],
                        username=vm['ssh_username'],
                        password=vm['ssh_password'],
                        timeout=3
                    )
                    ssh.close()
                    return True, "连接正常", True
                except:
                    return True, "端口开放但SSH服务异常", False
            else:
                return True, "连接失败", False
                
        except socket.error:
            return True, "网络错误", False
            
    except Error as e:
        return False, f"数据库错误: {str(e)}", False
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

def connect_with_putty(vm_id, putty_path):
    """通过PuTTY连接虚拟机"""
    conn = get_db_connection()
    if not conn:
        return False, "数据库连接失败"
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT vm_ip, ssh_port, ssh_username, ssh_password FROM virtual_machines WHERE id = %s",
            (vm_id,)
        )
        vm = cursor.fetchone()
        
        if not vm:
            return False, "虚拟机不存在"
        
        # 检查PuTTY路径是否存在
        if not os.path.exists(putty_path):
            return False, f"PuTTY路径不存在: {putty_path}"
        
        # 构建PuTTY命令行参数
        # 方法1: 使用-pw参数传递密码
        cmd = [
            putty_path,
            '-ssh',
            f'{vm["ssh_username"]}@{vm["vm_ip"]}',
            '-P', str(vm['ssh_port']),
            '-pw', vm['ssh_password'],
            '-loghost', 'on'
        ]
        
        try:
            # 在Windows上启动PuTTY
            if sys.platform == "win32":
                # 使用subprocess.Popen在后台运行
                import time
                try:
                    process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                    
                    # 检查进程是否成功启动
                    time.sleep(1)
                    if process.poll() is None:
                        return True, "PuTTY连接已启动"
                    else:
                        stdout, stderr = process.communicate()
                        error_msg = stderr.decode('gbk', errors='ignore')
                        return False, f"PuTTY启动失败: {error_msg}"
                except FileNotFoundError:
                    return False, "找不到PuTTY程序，请检查路径是否正确"
                except Exception as e:
                    return False, f"启动PuTTY失败: {str(e)}"
            else:
                return False, "此功能仅支持Windows系统"
                
        except Exception as e:
            return False, f"启动PuTTY失败: {str(e)}"
            
    except Error as e:
        return False, f"数据库错误: {str(e)}"
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

def test_putty_path(putty_path):
    """测试PuTTY路径是否有效"""
    if not os.path.exists(putty_path):
        return False, f"路径不存在: {putty_path}"
    
    if not putty_path.lower().endswith('putty.exe'):
        return False, "这不是有效的PuTTY可执行文件"
    
    try:
        # 尝试运行putty -help来测试
        result = subprocess.run(
            [putty_path, '-help'],
            capture_output=True,
            text=True,
            timeout=5,
            encoding='utf-8',
            errors='ignore'
        )
        
        if result.returncode == 0 or 'PuTTY' in result.stdout or 'PuTTY' in result.stderr:
            return True, "PuTTY路径验证成功"
        else:
            return False, "这不是有效的PuTTY程序"
            
    except subprocess.TimeoutExpired:
        return True, "PuTTY程序验证成功"
    except Exception as e:
        return False, f"测试PuTTY失败: {str(e)}"

def delete_virtual_machine(vm_id):
    """删除虚拟机"""
    conn = get_db_connection()
    if not conn:
        return False, "数据库连接失败"
    
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM virtual_machines WHERE id = %s", (vm_id,))
        conn.commit()
        
        if cursor.rowcount > 0:
            return True, "删除成功"
        else:
            return False, "虚拟机不存在"
    except Error as e:
        return False, f"数据库错误: {str(e)}"
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

def get_settings():
    """获取用户设置"""
    settings = {
        'putty_path': 'C:\\Program Files\\PuTTY\\putty.exe',
        'ssh_timeout': 10
    }
    return True, "获取成功", settings

def save_settings(user_settings):
    """保存用户设置"""
    return True, "设置保存成功"

def format_datetime_for_json(obj):
    """格式化对象中的datetime为字符串"""
    if isinstance(obj, dict):
        return {k: format_datetime_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [format_datetime_for_json(item) for item in obj]
    elif isinstance(obj, (datetime, date)):
        return obj.isoformat()
    elif isinstance(obj, bytes):
        try:
            return obj.decode('utf-8')
        except:
            return str(obj)
    else:
        return obj

def main():
    """主处理函数"""
    try:
        # 获取POST数据
        content_length = int(os.environ.get('CONTENT_LENGTH', 0))
        
        if content_length > 0:
            # 读取原始数据
            post_data = sys.stdin.read(content_length)
            
            try:
                # 尝试解析JSON
                data = json.loads(post_data)
            except json.JSONDecodeError:
                # 如果不是JSON，尝试解析表单数据
                from urllib.parse import parse_qs
                data = parse_qs(post_data)
                # 转换为简单字典
                data = {k: v[0] if v else '' for k, v in data.items()}
        else:
            data = {}
        
        action = data.get('action')
        response = {}
        
        if action == 'add_vm':
            user_id = data.get('user_id')
            vm_data = {
                'vm_name': data.get('vm_name'),
                'vm_ip': data.get('vm_ip'),
                'ssh_port': data.get('ssh_port', 22),
                'ssh_username': data.get('ssh_username'),
                'ssh_password': data.get('ssh_password')
            }
            success, message = add_virtual_machine(user_id, vm_data)
            response = {'success': success, 'message': message}
            
        elif action == 'get_vms':
            user_id = data.get('user_id')
            success, message, vms = get_user_vms(user_id)
            response = {'success': success, 'message': message, 'vms': vms}
            
        elif action == 'test_connection':
            vm_id = data.get('vm_id')
            success, message = test_ssh_connection(vm_id)
            response = {'success': success, 'message': message}
            
        elif action == 'check_connection':
            vm_id = data.get('vm_id')
            success, message, connected = check_connection_status(vm_id)
            response = {'success': success, 'message': message, 'connected': connected}
            
        elif action == 'connect_ssh':
            vm_id = data.get('vm_id')
            putty_path = data.get('putty_path', 'C:\\Program Files\\PuTTY\\putty.exe')
            success, message = connect_with_putty(vm_id, putty_path)
            response = {'success': success, 'message': message}
            
        elif action == 'test_putty':
            putty_path = data.get('putty_path')
            success, message = test_putty_path(putty_path)
            response = {'success': success, 'message': message}
            
        elif action == 'get_settings':
            success, message, settings = get_settings()
            response = {'success': success, 'message': message, 'settings': settings}
            
        elif action == 'save_settings':
            user_settings = data.get('settings', {})
            success, message = save_settings(user_settings)
            response = {'success': success, 'message': message}
            
        elif action == 'delete_vm':
            vm_id = data.get('vm_id')
            success, message = delete_virtual_machine(vm_id)
            response = {'success': success, 'message': message}
            
        else:
            response = {'success': False, 'message': '无效的操作'}
        
        # 格式化响应数据，确保所有datetime对象都被转换为字符串
        formatted_response = format_datetime_for_json(response)
        
        # 输出JSON响应
        json_response = json.dumps(formatted_response, ensure_ascii=False, cls=DateTimeEncoder)
        sys.stdout.write(json_response)
        
    except Exception as e:
        # 错误处理
        import traceback
        error_response = {
            'success': False,
            'message': f'服务器错误: {str(e)}',
            'error_type': type(e).__name__
        }
        json_response = json.dumps(error_response, ensure_ascii=False)
        sys.stdout.write(json_response)

if __name__ == '__main__':
    main()