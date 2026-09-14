#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import cgi
import cgitb
import json
import hashlib
import mysql.connector
from mysql.connector import Error

cgitb.enable()  # 启用错误显示

# 数据库配置
DB_CONFIG = {
    'host': 'localhost',
    'database': 'vm_management',
    'user': 'root',
    'password': '123456',  # 填写你的MySQL密码
    'charset': 'utf8mb4'
}

def get_db_connection():
    """获取数据库连接"""
    try:
        return mysql.connector.connect(**DB_CONFIG)
    except Error as e:
        print(f"Database connection error: {e}")
        return None

def hash_password(password):
    """使用SHA-256加密密码"""
    return hashlib.sha256(password.encode()).hexdigest()

def register_user(username, email, password):
    """注册新用户"""
    conn = get_db_connection()
    if not conn:
        return False, "数据库连接失败"
    
    try:
        cursor = conn.cursor()
        hashed_pwd = hash_password(password)
        
        # 检查用户名是否已存在
        cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
        if cursor.fetchone():
            return False, "用户名已存在"
        
        # 检查邮箱是否已存在
        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
            return False, "邮箱已存在"
        
        # 插入新用户
        cursor.execute(
            "INSERT INTO users (username, email, password) VALUES (%s, %s, %s)",
            (username, email, hashed_pwd)
        )
        conn.commit()
        return True, "注册成功"
    except Error as e:
        return False, f"数据库错误: {str(e)}"
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def login_user(username, password):
    """用户登录验证"""
    conn = get_db_connection()
    if not conn:
        return False, "数据库连接失败"
    
    try:
        cursor = conn.cursor(dictionary=True)
        hashed_pwd = hash_password(password)
        
        cursor.execute(
            "SELECT id, username FROM users WHERE username = %s AND password = %s",
            (username, hashed_pwd)
        )
        user = cursor.fetchone()
        
        if user:
            return True, "登录成功", user
        else:
            return False, "用户名或密码错误", None
    except Error as e:
        return False, f"数据库错误: {str(e)}", None
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def main():
    """主处理函数"""
    print("Content-Type: application/json\n")
    
    try:
        # 获取POST数据
        data = json.loads(cgi.FieldStorage().getvalue('POST_DATA', ''))
        action = data.get('action')
        
        response = {}
        
        if action == 'register':
            username = data.get('username')
            email = data.get('email')
            password = data.get('password')
            
            success, message = register_user(username, email, password)
            response = {'success': success, 'message': message}
            
        elif action == 'login':
            username = data.get('username')
            password = data.get('password')
            
            success, message, user = login_user(username, password)
            if success:
                response = {
                    'success': True,
                    'message': message,
                    'user_id': user['id'],
                    'username': user['username']
                }
            else:
                response = {'success': False, 'message': message}
        else:
            response = {'success': False, 'message': '无效的操作'}
        
        print(json.dumps(response))
        
    except Exception as e:
        print(json.dumps({'success': False, 'message': f'服务器错误: {str(e)}'}))

if __name__ == '__main__':
    main()