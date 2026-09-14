#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import cgi
import cgitb
import json
import mysql.connector
import paramiko
from mysql.connector import Error

cgitb.enable()

# 数据库配置
DB_CONFIG = {
    'host': 'localhost',
    'database': 'vm_management',
    'user': 'root',
    'password': '123456',
    'charset': 'utf8mb4'
}

def get_db_connection():
    """获取数据库连接"""
    try:
        return mysql.connector.connect(**DB_CONFIG)
    except Error as e:
        print(f"Database connection error: {e}")
        return None

def add_virtual_machine(user_id, vm_data):
    """添加虚拟机"""
    conn = get_db_connection()
    if not conn:
        return False, "数据库连接失败"
    
    try:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO virtual_machines 
               (user_id, vm_name, vm_ip, ssh_port, ssh_username, ssh_password) 
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (user_id, vm_data['vm_name'], vm_data['vm_ip'], 
             vm_data['ssh_port'], vm_data['ssh_username'], 
             vm_data['ssh_password'])
        )
        conn.commit()
        return True, "虚拟机添加成功"
    except Error as e:
        return False, f"数据库错误: {str(e)}"
    finally:
        if conn.is_connected():
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
            "SELECT id, vm_name, vm_ip, ssh_port, ssh_username FROM virtual_machines WHERE user_id = %s",
            (user_id,)
        )
        vms = cursor.fetchall()
        return True, "获取成功", vms
    except Error as e:
        return False, f"数据库错误: {str(e)}", []
    finally:
        if conn.is_connected():
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
            stdin, stdout, stderr = ssh.exec_command('echo "SSH Connection Test Successful"')
            output = stdout.read().decode().strip()
            
            ssh.close()
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
        if conn.is_connected():
            cursor.close()
            conn.close()

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
        if conn.is_connected():
            cursor.close()
            conn.close()

def main():
    """主处理函数"""
    print("Content-Type: application/json\n")
    
    try:
        data = json.loads(cgi.FieldStorage().getvalue('POST_DATA', ''))
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
            
        elif action == 'delete_vm':
            vm_id = data.get('vm_id')
            success, message = delete_virtual_machine(vm_id)
            response = {'success': success, 'message': message}
            
        else:
            response = {'success': False, 'message': '无效的操作'}
        
        print(json.dumps(response))
        
    except Exception as e:
        print(json.dumps({'success': False, 'message': f'服务器错误: {str(e)}'}))

if __name__ == '__main__':
    main()