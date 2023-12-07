#!/usr/bin/env python3


from decimal import Decimal
import hashlib
import json
import os
import platform
import shutil
import sys
import threading
import time
import traceback
from dateutil import parser
from typing import Any, List, Union
from datetime import datetime, timezone
from pathlib import Path

from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *

import boto3
from botocore.exceptions import ClientError
from boto3.dynamodb.types import TypeDeserializer, TypeSerializer

import qtawesome as qta

import bigfoot_constants as constants

"""Since you're going to style almost everything, try to use
app.setStyle('fusion'), or eventually
self.setStyle(QStyleFactory.create('fusion')) in the subclass init.

https://matiascodesal.com/blog/spice-your-qt-python-font-awesome-icons/
"""

def create_sha256_hash_for_file(filepath):

    BUF_SIZE = 65536
    
    sha256 = hashlib.sha256()
    
    with open(filepath, 'rb') as f:
        while True:
            data = f.read(BUF_SIZE)
            if not data:
                break
            sha256.update(data)

    return sha256.hexdigest()


def create_DynamoDB_table(access_key_id, secret_access_key, table_name, attribute_name):

    try:
        # Get the service client.
        dynamodb = boto3.resource('dynamodb', aws_access_key_id=access_key_id,
                aws_secret_access_key=secret_access_key, region_name='us-west-2')

        # Create the DynamoDB table.
        table = dynamodb.create_table(
            TableName = f"{table_name}",
            KeySchema = [
                {
                    'AttributeName': attribute_name,
                    'KeyType': 'HASH'
                },
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': attribute_name,
                    'AttributeType': 'S'
                },
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            }
        )

        # Wait until the table exists.
        table.wait_until_exists()

    except ClientError as err:
        # logger.error(
        #     f'{table_name}, {email}, {err.response["Error"]["Code"]}, {err.response["Error"]["Message"]}'
        # )
        raise err
    
    return None


def delete_DynamoDB_table(access_key_id, secret_access_key, table_name):

    try:
        # Get the service client.
        dynamodb = boto3.client('dynamodb', aws_access_key_id=access_key_id,
                aws_secret_access_key=secret_access_key, region_name='us-west-2')

        # Delete the DynamoDB table.
        table = dynamodb.delete_table(
            TableName = f"{table_name}",
        )

    except ClientError as err:
        # logger.error(
        #     f'{table_name}, {email}, {err.response["Error"]["Code"]}, {err.response["Error"]["Message"]}'
        # )
        raise err
    
    return None


def get_item_from_DynamoDB_table(table_name, email):

    try:
        # Get the service resource.
        dynamodb = boto3.client('dynamodb', 
            aws_access_key_id=constants.AWS_ROOT_ACCESS_KEY_ID,
            aws_secret_access_key=constants.AWS_ROOT_SECRET_ACCESS_KEY, 
            region_name=constants.AWS_REGION)
        
        response = dynamodb.get_item(
            Key = {
                'email': {
                    'S': f'{email}',
                },
            },
            TableName = f'{table_name}',
        )
        
        if 'Item' not in response:
            return dict()
            
        else:
            python_data = dict()
        
            deserializer = TypeDeserializer()
            python_data = {k: deserializer.deserialize(v) for k,v in response['Item'].items()}
        
            return python_data
        
    except ClientError as err:
        # logger.error(
        #     f'{table_name}, {email}, {err.response["Error"]["Code"]}, {err.response["Error"]["Message"]}'
        # )
        raise err


def put_item_to_DynamoDB_table(table_name, data):

    try:
        ddb_data = json.loads(json.dumps(data), parse_float=Decimal)

        # Get the service resource.
        dynamodb = boto3.resource('dynamodb', aws_access_key_id=constants.AWS_ROOT_ACCESS_KEY_ID,
                                  aws_secret_access_key=constants.AWS_ROOT_SECRET_ACCESS_KEY, 
                                  region_name=constants.AWS_REGION)

        table = dynamodb.Table(table_name)

        response = table.put_item(
                Item = ddb_data
        )

    except ClientError as err:
        # logger.error(
        #     f'{table_name}, {email}, {err.response["Error"]["Code"]}, {err.response["Error"]["Message"]}'
        # )
        raise err


def add_s3_bucket_policy(access_key_id, secret_access_key, bucket_name, project_name, user):

    policy_dict = {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Sid": "AllowStatement3",
                            "Action": [
                                "s3:ListBucket"
                            ],
                            "Effect": "Allow",
                            "Resource": [
                                f"arn:aws:s3:::{bucket_name}"
                            ],
                            "Condition": {
                                "StringLike": {
                                    "s3:prefix": [
                                        f"{project_name}/*"
                                    ]
                                }
                            }
                        },
                        {
                            "Sid": "AllowStatement4A",
                            "Effect": "Allow",
                            "Action": [
                                "s3:*"
                            ],
                            "Resource": [
                                f"arn:aws:s3:::{bucket_name}/{project_name}/*"
                            ]
                        }
                    ]
                }

    try:
        s3 = boto3.client('s3', aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key)

        s3.put_bucket_policy(
            Bucket = bucket_name,
            Policy = json.dumps(policy_dict)
        )

    except ClientError as e:
        print(f"Unexpected error:  {e}")

    return None


def get_rmt_object_to_loc(access_key_id, secret_access_key, bucket_name, obj, filepath):

    try:
        s3 = boto3.resource('s3', aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key)
    
        response = s3.meta.client.download_file(bucket_name, obj, filepath)
    
    except ClientError as e:
        print(f"Unexpected error:  {e}")

    return response


def put_loc_object_to_rmt(access_key_id, secret_access_key, filepath, bucket_name, obj, sha256=''):

    try:
        s3 = boto3.client('s3', aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key)
    
        response = s3.upload_file(filepath, bucket_name, obj,
            ExtraArgs={
                "Metadata": {
                    "ChecksumSHA256": sha256
                }
            }
        )
    
    except ClientError as e:
        print(f"Unexpected error:  {e}")

    return response


def list_s3_bucket_contents(access_key_id, secret_access_key, bucket_name):

    try:
        s3 = boto3.client('s3', aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key)
    
        bucket_contents = s3.list_objects(
            Bucket = bucket_name,
        )
        
    except ClientError as e:
        print(f"Unexpected error:  {e}")

    return bucket_contents


def list_s3_bucket_contents_with_prefix(access_key_id, secret_access_key, bucket_name, prefix):

    try:
        s3 = boto3.client('s3', aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key)
    
        bucket_contents = s3.list_objects(
            Bucket = bucket_name,
            Prefix = prefix
        )
        
    except ClientError as e:
        print(f"Unexpected error:  {e}")

    return bucket_contents


def delete_s3_bucket_content_list(access_key_id, secret_access_key, bucket_name, content_list=None):

    try:
        s3 = boto3.client('s3', aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key)
    
        response = s3.delete_objects(
                Bucket = bucket_name,
                Delete = {"Objects": [{"Key": key} for key in content_list]}
            )
        
    except ClientError as e:
        print(f"Unexpected error:  {e}")

    return None


def does_object_exist_in_s3_bucket(access_key_id, secret_access_key, bucket_name, object_name):

    bucket_contents = list_s3_bucket_contents(access_key_id, secret_access_key, bucket_name)
        
    for obj in bucket_contents['Contents']:
        if str(object_name) ==  str(obj['Key']):
            return True
    
    return False


def get_rmt_project_object_versions(access_key_id, secret_access_key, bucket_name, project):

    try:
        s3 = boto3.client('s3', aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key)
    
        obj_versions = s3.list_object_versions(
                Bucket = bucket_name,
                Prefix = project
        )
        
    except ClientError as e:
        print(f"Unexpected error:  {e}")

    return obj_versions['Versions']


def get_last_modified_time_for_remote_project(access_key_id, secret_access_key, bucket_name, project):

    try:
        s3 = boto3.client('s3', aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key)
    
        bucket_contents = s3.list_objects(
            Bucket = bucket_name,
            Prefix = project
        )
        
        latest_modified = 0
        
        if 'Contents' in bucket_contents:
            for obj in bucket_contents['Contents']:
                if int(obj['LastModified'].timestamp()) > latest_modified:
                    latest_modified = int(obj['LastModified'].timestamp())

            return str(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(latest_modified)))
      
        else:
            return 'NO DATA'
                
    except ClientError as err:
        # logger.error(
        #     f'{table_name}, {email}, {err.response["Error"]["Code"]}, {err.response["Error"]["Message"]}'
        # )
        raise err


def get_last_modified_time_for_local_project(local_project_path):

    latest_modified = int(max(os.stat(root).st_mtime for root,_,_ in os.walk(local_project_path)))

    return str(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(latest_modified)))


def get_remote_object_metadata(access_key_id, secret_access_key, bucket_name, object_name):

    try:
        s3 = boto3.client('s3', aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key)
    
        response = s3.head_object(
            Bucket = bucket_name,
            Key = object_name
        )
        
        return response['ResponseMetadata']['HTTPHeaders']['x-amz-meta-checksumsha256']

    except ClientError as err:
        # logger.error(
        #     f'{table_name}, {email}, {err.response["Error"]["Code"]}, {err.response["Error"]["Message"]}'
        # )
        raise err


def run_fast_scandir(folder):

    subfolders, files, file_objects = [], [], []

    for f in os.scandir(folder):
        if f.name[0] == '.':
            pass
        elif f.is_dir():
            subfolders.append(f.path)
        elif f.is_file():
            # print(f.path, f.stat().st_size, time.ctime(os.path.getmtime(f.path)))
            files.append(f.path)
            file_objects.append(f)
        else:
            pass

    for subfolder in list(subfolders):
        sf, f, fo = run_fast_scandir(subfolder)
        subfolders.extend(sf)
        files.extend(f)
        file_objects.extend(fo)
        
    return subfolders, files, file_objects


def get_local_project_info(user_folder, project):

    local_project_files = []

    abs_project_path = user_folder + '/' + project
    _, _, project_file_objects = run_fast_scandir(abs_project_path)
    
    for obj in project_file_objects:
        local_file_data = {
                            'Key': obj.path.replace(user_folder + '/', ''),
                            'Size': obj.stat().st_size,
                            'LastModified': time.ctime(os.path.getmtime(obj.path))
                         }
        local_project_files.append(local_file_data)
    
    return local_project_files


class AllObjectAccess:

    all_objects = []
    user_info = dict()

    def __init__(self):
    
        AllObjectAccess.all_objects.append(self)

        return None


class LoginWidget(QWidget, AllObjectAccess):
    
    def __init__(self):
        super().__init__()
        
        self.class_name = 'LoginWidget'
        
        self.setWindowTitle(constants.LOGIN_WINDOW_TTL)
        self.setWindowIcon(QIcon(constants.LOGIN_WINDOW_ICON))
        self.setFixedSize(constants.LOGIN_WINDOW_W, constants.LOGIN_WINDOW_H)

        layout = QGridLayout()
        self.setLayout(layout)

        labels = {}
        self.lineEdits = {}

        labels['Email'] = QLabel('Email')
        labels['Email'].setStyleSheet(constants.LOGIN_LABEL_STYLE)
        labels['Password'] = QLabel('Password')
        labels['Password'].setStyleSheet(constants.LOGIN_LABEL_STYLE)
        labels['Email'].setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        labels['Password'].setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        self.lineEdits['Email'] = QLineEdit()
        self.lineEdits['Password'] = QLineEdit()
        self.lineEdits['Password'].setEchoMode(QLineEdit.EchoMode.Password)

        layout.addWidget(labels['Email'], 0, 0, 1, 1)
        layout.addWidget(self.lineEdits['Email'], 0, 1, 1, 3)
        layout.addWidget(labels['Password'], 1, 0, 1, 1)
        layout.addWidget(self.lineEdits['Password'], 1, 1, 1, 3)

        button_login = QPushButton('Log In To BigFoot', clicked=self.checkCredential)
        layout.addWidget(button_login, 2, 3, 1, 1)

        self.status = QLabel('')
        self.status.setStyleSheet(constants.LOGIN_STATUS_STYLE)
        layout.addWidget(self.status, 3, 0, 1, 3)
        
        return None


    def checkCredential(self):
        email = self.lineEdits['Email'].text()
        entered_password = self.lineEdits['Password'].text()
        
        db_res = None
        user_name = ''
        user_email = ''
        
        try:
            
            self.status.setText('Logging into BigFoot...')
            self.status.repaint()
            
            db_res = get_item_from_DynamoDB_table(constants.AWS_DYNAMODB_TABLE, email)
                
            if not db_res:
            
                self.status.setText(f"Invalid email/user {email}")
                self.status.repaint()
                time.sleep(constants.LOGIN_DELAY_SEC)
                self.status.setText(f"")
                self.status.repaint()
                self.lineEdits['Email'].clear()
                self.lineEdits['Password'].clear()
                    
                return None
            
            elif db_res["email"] == email and db_res["password"] != entered_password:
            
                self.status.setText(f"Invalid password for {email}")
                self.status.repaint()
                time.sleep(constants.LOGIN_DELAY_SEC)
                self.status.setText(f"")
                self.status.repaint()
                self.lineEdits['Email'].clear()
                self.lineEdits['Password'].clear()
                    
                return None
                    
            elif db_res["email"] == email and db_res["password"] == entered_password:
            
                user_info_keys = ['first_name', 'last_name', 'email', 
                                  'password', 'user_image',
                                  'date_time_epoch_join', 
                                  'user_AWS_ACCESS_KEY_ID', 
                                  'user_AWS_SECRET_ACCESS_KEY', 
                                  'user_AWS_BUCKET_NAME', 'projects']
                                  
                for key in user_info_keys:
                    AllObjectAccess.user_info[key] = db_res[key]
                    
                get_rmt_object_to_loc(AllObjectAccess.user_info['user_AWS_ACCESS_KEY_ID'],
                                      AllObjectAccess.user_info['user_AWS_SECRET_ACCESS_KEY'], 
                                      AllObjectAccess.user_info['user_AWS_BUCKET_NAME'], 
                                      AllObjectAccess.user_info['user_image'], './.user_image.jpg')
                    
            else:
                
                sys.exit()
            
        except Exception as e:
            self.status.setText("Login Error")
            self.status.repaint()
            print(f"Error: {e}")
            time.sleep(3)
            sys.exit()

        self.config_file = Path('./config.json')
        
        if not self.config_file.is_file():
            self.create_config_file = CreateConfigFile()
            self.create_config_file.show()
            self.close()
            return None
            
        elif self.config_file.is_file(): 
            self.mainApp = AppMainWindow()
            self.mainApp.show()        
            self.close()
            return None
            
        else:
            self.close()
            sys.exit()
        

class CreateConfigFile(QWidget, AllObjectAccess):
    def __init__(self):
        super(CreateConfigFile, self).__init__()
        self.class_name = 'CreateConfigFile'
        self.setWindowTitle(constants.MAIN_WINDOW_TTL)
        self.setWindowIcon(QIcon(constants.MAIN_WINDOW_ICON))
        self.layout = QHBoxLayout(self)
        self.create_config_button = QPushButton('Create BigFoot Configuration File', clicked=self.create_cofig_file)
        self.layout.addWidget(self.create_config_button, alignment=(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignAbsolute | Qt.AlignmentFlag.AlignTop), stretch=2)
        self.setLayout(self.layout)
        self.resize(constants.MAIN_WINDOW_W, constants.MAIN_WINDOW_H)
            
    def create_cofig_file(self):
        config = dict()
        projects_directory = str(QFileDialog.getExistingDirectory(self, "Select Directory"))
        
        config['config_create_time'] = datetime.now(timezone.utc).isoformat()
        
        config['projects_directory'] = projects_directory
        
        config['system_platform'] = {
                                        'machine': platform.machine(),
                                        'processor': platform.processor(),
                                        'system': platform.system(),
                                        'platform': platform.platform(),
                                        'version': platform.version()
                                   }
        
        with open('./config.json', 'w') as config_file:
            json.dump(config, config_file, sort_keys=True, indent=4)
            
        self.mainApp = AppMainWindow()
        self.mainApp.show()        
        self.close()
        
        return None


class AppMainWindow(QWidget, AllObjectAccess):
    def __init__(self):
        super(AppMainWindow, self).__init__()
        self.class_name = 'AppMainWindow'
        self.setWindowTitle(constants.MAIN_WINDOW_TTL)
        self.setWindowIcon(QIcon(constants.MAIN_WINDOW_ICON))
        self.layout = QHBoxLayout(self)        
        self.left_panel = LeftPanel()
        self.left_panel.setStyleSheet(constants.MAIN_STYLE)
        self.layout.addWidget(self.left_panel, alignment=(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignAbsolute | Qt.AlignmentFlag.AlignTop), stretch=1)
        self.vertical_line = VerticalLine1()
        self.layout.addWidget(self.vertical_line, alignment=(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignAbsolute | Qt.AlignmentFlag.AlignTop), stretch=1)
        self.right_panel = RightPanel()
        self.right_panel.setStyleSheet(constants.MAIN_STYLE)
        self.layout.addWidget(self.right_panel, alignment=(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignAbsolute | Qt.AlignmentFlag.AlignTop), stretch=2)
        self.layout.addStretch()
        self.setLayout(self.layout)
        self.resize(constants.MAIN_WINDOW_W, constants.MAIN_WINDOW_H)
        return None


class LeftPanel(QWidget, AllObjectAccess):
    def __init__(self):
        super(LeftPanel, self).__init__()
        self.class_name = 'LeftPanel'
        self.setWindowTitle(constants.LEFT_PANEL_TTL)
        self.setWindowIcon(QIcon(constants.LEFT_PANEL_WINDOW_ICON))
        self.layout = QVBoxLayout()
        # self.layout.setSpacing(0)
        self.setLayout(self.layout)
        self.line_1 = LeftPanelLine1()
        self.line_1.setStyleSheet(constants.LEFT_PANEL_STATUS_STYLE)
        self.layout.addWidget(self.line_1, stretch=1)
        self.line_2 = LeftPanelLine2()
        self.line_2.setStyleSheet(constants.LEFT_PANEL_STATUS_STYLE)
        self.layout.addWidget(self.line_2, stretch=1)
        self.horizontal_line_1 = LeftPanelHorizontalLine1()
        self.layout.addWidget(self.horizontal_line_1, alignment=Qt.AlignmentFlag.AlignTop, stretch=1)
        self.projects_directory = LeftPanelFileDir1()
        self.layout.addWidget(self.projects_directory, alignment=Qt.AlignmentFlag.AlignTop, stretch=1)
        self.projects_directory.hide()
        self.horizontal_line_2 = LeftPanelHorizontalLine1()
        self.layout.addWidget(self.horizontal_line_2, alignment=Qt.AlignmentFlag.AlignTop, stretch=1)
        
        self.layout.addStretch()
        
        self.close_all = QPushButton('Close All Windows', clicked=self.close_all)
        self.close_all.setStyleSheet(constants.LEFT_PANEL_CLOSE_ALL_WINDOWS_STYLE)
        self.close_all.setFixedHeight(50)
        self.layout.addWidget(self.close_all)
        
        # self.setLayout(self.layout)
        self.resize(constants.LEFT_PANEL_WINDOW_W, constants.LEFT_PANEL_WINDOW_H)
        return None
        
    def close_all(self):
        QApplication.closeAllWindows()
        raise SystemExit
        return None


class LeftPanelLine1(QWidget, AllObjectAccess):
    def __init__(self):
        super(LeftPanelLine1, self).__init__()
        self.class_name = 'LeftPanelLine1'
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.layout = QHBoxLayout(self)
        self.user_image = QLabel(self)
        self.user_pixmap = QPixmap('./.user_image.jpg')
        self.user_image.setPixmap(self.user_pixmap)
        self.user_image.setStyleSheet(constants.LEFT_PANEL_LINE_1_STYLE)
        self.user_image.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.user_name = QLabel(AllObjectAccess.user_info['first_name'] + ' ' + AllObjectAccess.user_info['last_name'])
        self.user_name.setStyleSheet(constants.LEFT_PANEL_LINE_1_STYLE)
        self.user_name.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.settings = QPushButton('Settings', clicked=self.settings_execute_when_clicked)
        self.settings.setStyleSheet("QPushButton { font-size: 14px; background-color: transparent; border: 0px }")
        self.settings.setFixedSize(QSize(120, 50))
        self.settings_icon = qta.icon(constants.LEFT_PANEL_LINE_1_SETTINGS_ICON, color='#000000')
        self.settings.setIcon(self.settings_icon)
        self.settings.setIconSize(QSize(50, 50))
        self.layout.addWidget(self.user_image, stretch=2)
        self.layout.addWidget(self.user_name, stretch=2)
        self.layout.addWidget(self.settings, stretch=2)
        self.setLayout(self.layout)
        return None
        
    def settings_execute_when_clicked(self):
        print('Display application settings!!!\n')
        return None
        

class LeftPanelLine2(QWidget, AllObjectAccess):
    def __init__(self):
        super(LeftPanelLine2, self).__init__()
        self.class_name = 'LeftPanelLine2'
        self.layout = QHBoxLayout(self)
        self.projects_folder_button = QPushButton('BigFoot FOLDER', clicked=self.projects_folder_toggle)
        self.projects_folder_button.setStyleSheet(constants.LEFT_PANEL_LINE_2_FOLDER_STYLE)
        self.folder_cls = getattr(QStyle.StandardPixmap, constants.LEFT_PANEL_LINE_2_FOLDER_CLOSED)
        self.folder_opn = getattr(QStyle.StandardPixmap, constants.LEFT_PANEL_LINE_2_FOLDER_OPEN)
        self.icon_cls = QPixmap(self.style().standardPixmap(self.folder_cls))
        self.icon_opn = QPixmap(self.style().standardPixmap(self.folder_opn))
        self.folder_icon = QIcon()
        self.folder_icon.addPixmap(self.icon_cls, QIcon.Mode.Normal, QIcon.State.Off)
        self.folder_icon.addPixmap(self.icon_opn, QIcon.Mode.Active, QIcon.State.On)
        self.projects_folder_button.setIcon(self.folder_icon)
        self.projects_folder_button.setCheckable(True)
        self.projects_folder_button.setIconSize(QSize(50, 50))
        self.layout.addWidget(self.projects_folder_button, alignment=(Qt.AlignmentFlag.AlignLeft))
        self.new_project = QPushButton('New Project', clicked=self.create_new_project)
        self.new_project.setStyleSheet("QPushButton { font-size: 14px; background-color: transparent; border: 0px }")
        self.new_project.setFixedSize(QSize(120, 50))
        self.new_project_icon = qta.icon(constants.LEFT_PANEL_LINE_2_NEW_PROJECT_ICON, color='#000000')
        self.new_project.setIcon(self.new_project_icon)
        self.new_project.setIconSize(QSize(40, 40))
        self.layout.addWidget(self.new_project, alignment=(Qt.AlignmentFlag.AlignRight))
        self.setLayout(self.layout)
        self.resize(constants.LEFT_PANEL_WINDOW_W, constants.LEFT_PANEL_WINDOW_H)
        return None
        
    def projects_folder_toggle(self):
    
        dir_object = None
        right_panel_object = None
        right_panel_line1_object = None
        right_panel_info_panels_object = None
    
        for obj in AllObjectAccess.all_objects:
                if obj.class_name == 'LeftPanelFileDir1':
                    dir_object = obj
                if obj.class_name == 'RightPanel':
                    right_panel_object = obj
                if obj.class_name == 'RightPanelLine1':
                    right_panel_line1_object = obj
                if obj.class_name == 'RightPanelInfoPanels':
                    right_panel_info_panels_object = obj
                
    
        if self.projects_folder_button.isChecked():
            if dir_object:
                dir_object.show()
            if right_panel_line1_object:
                # right_panel_line1_object.show()
                pass
        else:
            if dir_object:
                dir_object.hide()
                dir_object.treeview.clearSelection()
            if right_panel_line1_object:
                right_panel_line1_object.hide()
                right_panel_line1_object.user_pixmap = QPixmap(None)
                right_panel_line1_object.user_image.clear()
                right_panel_line1_object.project_name_label.setText(None)
                right_panel_line1_object.user_name.setText(None)
            if right_panel_info_panels_object:
                right_panel_info_panels_object.hide()
                
            for obj in AllObjectAccess.all_objects:
                if obj.class_name == 'LocalProjectFolder':
                    obj.close()
        
    def create_new_project(self):
        self.new_project = CreateNewProject()
        self.new_project.show()
        return None
        

class CreateNewProject(QWidget, AllObjectAccess):

    def __init__(self):
        super().__init__()
        self.class_name = 'CreateNewProject'
        self.setWindowTitle(constants.CREATE_NEW_PROJECT_WINDOW_TTL)
        self.setWindowIcon(QIcon(constants.CREATE_NEW_PROJECT_WINDOW_ICON))
        self.setFixedSize(constants.CREATE_NEW_PROJECT_WINDOW_W, constants.CREATE_NEW_PROJECT_WINDOW_H)
        
        self.user_AWS_ACCESS_KEY_ID = AllObjectAccess.user_info['user_AWS_ACCESS_KEY_ID']
        self.user_AWS_SECRET_ACCESS_KEY = AllObjectAccess.user_info['user_AWS_SECRET_ACCESS_KEY']
        self.user_AWS_BUCKET_NAME = AllObjectAccess.user_info['user_AWS_BUCKET_NAME']

        self.project_image_path = None

        layout = QGridLayout()

        labels = {}
        self.lineEdits = {}
        
        keep_size_when_hidden = QSizePolicy()
        keep_size_when_hidden.setRetainSizeWhenHidden(True)

        labels['New Project Name'] = QLabel('New Project Name')
        labels['New Project Name'].setStyleSheet(constants.CREATE_NEW_PROJECT_LABEL_STYLE)
        labels['Project Image'] = QLabel('Project Image')
        # labels['none'].setSizePolicy(keep_size_when_hidden)
        labels['Project Image'].setStyleSheet(constants.CREATE_NEW_PROJECT_LABEL_STYLE)
        labels['New Project Name'].setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        labels['Project Image'].setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        self.lineEdits['New Project Name'] = QLineEdit()
        self.lineEdits['Project Image'] = QLineEdit()
        # self.lineEdits['none'].setSizePolicy(keep_size_when_hidden)
        # self.lineEdits['none'].setEchoMode(QLineEdit.EchoMode.Password)

        layout.addWidget(labels['New Project Name'], 0, 0, 1, 1)
        layout.addWidget(self.lineEdits['New Project Name'], 0, 1, 1, 3)
        layout.addWidget(labels['Project Image'], 1, 0, 1, 1)
        layout.addWidget(self.lineEdits['Project Image'], 1, 1, 1, 3)

        test = QPushButton('Select Project Image (Optional)', clicked=self.select_project_image)
        layout.addWidget(test, 2, 3, 1, 1)

        button_create_project = QPushButton('Create Project', clicked=self.create_project)
        layout.addWidget(button_create_project, 3, 3, 1, 1)
        
        button_delete_project = QPushButton('Delete Project (for debug)', clicked=self.delete_project)
        layout.addWidget(button_delete_project, 4, 3, 1, 1)
        
        self.status = QLabel('')
        self.status.setStyleSheet(constants.CREATE_NEW_PROJECT_STATUS_STYLE)
        layout.addWidget(self.status, 4, 0, 1, 3)
        
        self.setLayout(layout)
              
        # labels['none'].hide()
        # self.lineEdits['none'].hide()
        
        return None
        
    def select_project_image(self):
        
        project_image, ok = QFileDialog.getOpenFileName()
        
        if project_image:
            self.project_image_path = Path(project_image)
            self.lineEdits['Project Image'].setText(str(self.project_image_path))
        
        return None

    def create_project(self):
    
        self.new_project_name = self.lineEdits['New Project Name'].text()
        
        if not self.new_project_name:
            self.status.setText('Enter valid project name')
            self.status.repaint()
            time.sleep(constants.CREATE_NEW_PROJECT_DELAY_SEC)
            self.status.setText(f"")
            self.status.repaint()
            self.lineEdits['New Project Name'].clear()
            
            return None
            
        if len(self.new_project_name) > 20:
            self.status.setText('Project name must be 20 characters or less')
            self.status.repaint()
            time.sleep(constants.CREATE_NEW_PROJECT_DELAY_SEC)
            self.status.setText(f"")
            self.status.repaint()
            self.lineEdits['New Project Name'].clear()

            return None
            
        unallowed_chars = list('~`!@#$%^&*()+= :;"{}[]|<,>?\\/')
        
        if any(c in self.new_project_name for c in unallowed_chars):
            self.status.setText('~`!@#$%^&*()+= :;"{}[]|<,>?\\/ PROHIBITED')
            self.status.repaint()
            time.sleep(constants.CREATE_NEW_PROJECT_DELAY_SEC)
            self.status.setText(f"")
            self.status.repaint()
            self.lineEdits['New Project Name'].clear()

            return None
        
        try:
            self.status.setText('Creating new project on LOCAL and REMOTE...')
            self.status.repaint()
                             
            cfg_data = dict()
            with open('./config.json', 'r') as config_file:
                cfg_data = json.load(config_file)

            new_project_local = cfg_data['projects_directory'] + '/' + self.new_project_name
            
            empty_file_for_S3_folder_creation = '.empty_file'
            empty_file_filepath = Path(cfg_data['projects_directory'] + '/' + empty_file_for_S3_folder_creation)
            
            if not empty_file_filepath.is_file():            
                open(empty_file_filepath, 'a').close()
            
            put_loc_object_to_rmt(self.user_AWS_ACCESS_KEY_ID, self.user_AWS_SECRET_ACCESS_KEY, empty_file_filepath, self.user_AWS_BUCKET_NAME, self.new_project_name + '/')
            
            if self.project_image_path:
                put_loc_object_to_rmt(self.user_AWS_ACCESS_KEY_ID, self.user_AWS_SECRET_ACCESS_KEY, self.project_image_path, self.user_AWS_BUCKET_NAME, self.new_project_name + '/project_image.jpg')
            
            Path(new_project_local).mkdir(parents=False, exist_ok=False)
            
            upload_comment_dynamo_db = self.user_AWS_BUCKET_NAME + '_' + self.new_project_name
            attribute_name = 'utc_time'  # <-- This will need to change!!!
            create_DynamoDB_table(constants.AWS_ROOT_ACCESS_KEY_ID,
                                  constants.AWS_ROOT_SECRET_ACCESS_KEY, 
                                  upload_comment_dynamo_db, 
                                  attribute_name)
            
            current_utc = int(time.time())
            user_name = AllObjectAccess.user_info['first_name'] + ' ' + AllObjectAccess.user_info['last_name']
            user_email = AllObjectAccess.user_info['email']

            new_project_creation_entry = {
                        "action": 'CREATED',
                        "utc_time": str(current_utc),
                        "user_name": user_name,
                        "user_email": user_email,
                        "upload_comment": "Project created.",
                        "files_uploaded": []
                       }  
            
            put_item_to_DynamoDB_table(upload_comment_dynamo_db, new_project_creation_entry)

            # print(json.dumps(new_project_creation_entry, sort_keys=False, indent=4))
            
            new_owner_project = {
                                    'bucket': self.user_AWS_BUCKET_NAME,
                                    'folder': self.new_project_name,
                                    'status': 'owner',
                                    'project_owner': AllObjectAccess.user_info['first_name'] + ' ' + AllObjectAccess.user_info['last_name'],
                                    'project_owner_email': AllObjectAccess.user_info['email'],
                                    'upload_comments_db': upload_comment_dynamo_db
                                }
                                
            update_dict = get_item_from_DynamoDB_table(constants.AWS_DYNAMODB_TABLE, AllObjectAccess.user_info['email'])
            
            update_dict['projects'][self.new_project_name] = new_owner_project
            
            put_item_to_DynamoDB_table(constants.AWS_DYNAMODB_TABLE, update_dict)
                          
            self.status.setText('New project created')
            self.status.repaint()
            
            time.sleep(3)
            
            self.status.setText('')
            self.status.repaint()
            
        except ClientError as e:   
            self.status.setText(e.response['Error']['Code'])
            self.status.repaint()
            time.sleep(3)
            
            self.status.setText('')
            self.status.repaint()
            self.lineEdits['New Project Name'].clear()
            
            self.close()
            return None
                       
        self.status.setText('')
        self.status.repaint()
        self.lineEdits['New Project Name'].clear()
        
        self.close()
        
        return None

    def delete_project(self):
        self.status.setText('Deleting project on LOCAL and REMOTE if it exists...')
        self.status.repaint()
        
        self.new_project_name = self.lineEdits['New Project Name'].text()
        
        delete_DynamoDB_table(constants.AWS_ROOT_ACCESS_KEY_ID,
                              constants.AWS_ROOT_SECRET_ACCESS_KEY,  
                              self.user_AWS_BUCKET_NAME + '_' + self.new_project_name)
        
        project_contents = list_s3_bucket_contents_with_prefix(self.user_AWS_ACCESS_KEY_ID,
                                                              self.user_AWS_SECRET_ACCESS_KEY, 
                                                              self.user_AWS_BUCKET_NAME, 
                                                              self.new_project_name)
        
        delete_these_objects_in_S3 = []
        
        for obj in project_contents['Contents']:
            delete_these_objects_in_S3.append(obj['Key'])
        
        delete_s3_bucket_content_list(self.user_AWS_ACCESS_KEY_ID,
                                      self.user_AWS_SECRET_ACCESS_KEY, 
                                      self.user_AWS_BUCKET_NAME, 
                                      delete_these_objects_in_S3)
        
        cfg_data = dict()
        with open('./config.json', 'r') as config_file:
            cfg_data = json.load(config_file)

        delete_this_dir = cfg_data['projects_directory'] + '/' + self.new_project_name
        
        shutil.rmtree(delete_this_dir, ignore_errors=True)
        
        update_dict = get_item_from_DynamoDB_table(constants.AWS_DYNAMODB_TABLE, AllObjectAccess.user_info['email'])
            
        update_dict['projects'].pop(self.new_project_name, None)
            
        put_item_to_DynamoDB_table(constants.AWS_DYNAMODB_TABLE, update_dict)
        
        self.status.setText('Project deleted')
        self.status.repaint()
            
        time.sleep(3)
        
        self.status.setText('')
        self.status.repaint()
        self.lineEdits['New Project Name'].clear()
        
        self.close()
        
        return None


class LeftPanelHorizontalLine1(QFrame, AllObjectAccess):
    def __init__(self):
        super(LeftPanelHorizontalLine1, self).__init__() 
        self.class_name = 'LeftPanelHorizontalLine1'
        self.setFrameShape(QFrame.Shape.HLine)
        self.setFrameShadow(QFrame.Shadow.Sunken)
        self.setFixedHeight(10)
        self.setStyleSheet(constants.LEFT_PANEL_HORIZONTAL_LINE_STYLE)
        return None


class IconProvider(QFileIconProvider):
    def icon(self, fileInfo):
        if fileInfo.isDir():  # mdi6.weather-cloudy, mdi.cloud-outline
            return qta.icon('mdi.cloud-outline',
                            color_off='black',
                            color_off_active='blue',
                            color_on='#FE1493',
                            color_on_active='#FE1493')
        return QFileIconProvider.icon(self, fileInfo)


class LeftPanelFileDir1(QWidget, AllObjectAccess):
    def __init__(self):
        super(LeftPanelFileDir1, self).__init__()
        self.class_name = 'LeftPanelFileDir1'
        self.dirModel = QFileSystemModel()
        self.dirModel.setIconProvider(IconProvider())
        
        self.cfg_data = dict()
        with open('./config.json', 'r') as config_file:
            self.cfg_data = json.load(config_file)
        
        self.dirModel.setRootPath(self.cfg_data['projects_directory'])
        self.dirModel.setFilter(QDir.Filter.NoDotAndDotDot | QDir.Filter.AllEntries)
        self.treeview = QTreeView()
        self.treeview.setFixedHeight(225)
        self.treeview.setStyleSheet(constants.LEFT_PANEL_FILE_DIR_STYLE)
        self.treeview.setModel(self.dirModel)
        self.treeview.setItemsExpandable(False)
        self.treeview.setSortingEnabled(True)
        self.treeview.sortByColumn(1, Qt.SortOrder.AscendingOrder)
        self.treeview.setAlternatingRowColors(False)
        self.treeview.setModel(self.dirModel)
        
        for i in range(1, self.dirModel.columnCount() + 1):
            self.treeview.hideColumn(i)

        self.treeview.header().setVisible(False)
        self.treeview.setRootIndex(self.dirModel.index(self.cfg_data['projects_directory']))
        self.treeview.clicked.connect(self.select_project)
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.treeview)
        self.setLayout(self.layout)
        self.show()
        return None     

    def select_project(self, index):
        self.index = index
        self.dirModel.setRootPath('')
        self.dirModel.setRootPath(self.cfg_data['projects_directory'])
        self.treeview.setModel(self.dirModel)
        current_project_path = self.dirModel.fileInfo(index).absoluteFilePath()
        project_name = current_project_path.split('/')[-1]
        
        for obj in AllObjectAccess.all_objects:
            if obj.class_name == 'RightPanel':
                right_panel_object = obj

        right_panel_object.create_or_update_right_panel(current_project_path)
        return None
        

class VerticalLine1(QFrame, AllObjectAccess):
    def __init__(self):
        super(VerticalLine1, self).__init__()
        self.class_name = 'VerticalLine1'
        self.setFrameShape(QFrame.Shape.VLine)
        self.setFrameShadow(QFrame.Shadow.Sunken)
        self.setStyleSheet(constants.VERTICAL_LINE_STYLE)
        self.setMinimumSize(10, 650)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # self.resize(10, 650)  # (w, h)
        return None


class RightPanel(QWidget, AllObjectAccess):
    def __init__(self):
        super(RightPanel, self).__init__()
        self.class_name = 'RightPanel'
        self.setWindowTitle(constants.RIGHT_PANEL_TTL)
        self.setWindowIcon(QIcon(constants.RIGHT_PANEL_WINDOW_ICON))
        self.setFixedSize(constants.RIGHT_PANEL_WINDOW_W, constants.RIGHT_PANEL_WINDOW_H)
        return None
        
    def create_or_update_right_panel(self, current_project_path):
        self.left_panel_file_dir_1_object = None
        self.right_panel_line_1_object = None
        self.right_panel_info_panels_object = None
        
        self.current_project_path = current_project_path
        self.project_name = current_project_path.split('/')[-1]
        
        for obj in AllObjectAccess.all_objects:
            if obj.class_name == 'LeftPanelFileDir1':
                self.left_panel_file_dir_1_object = obj
            if obj.class_name == 'RightPanelLine1':
                self.right_panel_line_1_object = obj
            if obj.class_name == 'RightPanelInfoPanels':
                self.right_panel_info_panels_object = obj
                
        if not self.right_panel_line_1_object: 
            self.layout = QVBoxLayout()
            self.line_1 = RightPanelLine1(self.project_name)
            self.line_1.setStyleSheet(constants.RIGHT_PANEL_STATUS_STYLE)
            self.layout.addWidget(self.line_1, alignment=Qt.AlignmentFlag.AlignTop)
            self.layout.addStretch()
            self.folder_info_panels = RightPanelInfoPanels(current_project_path)
            self.layout.addWidget(self.folder_info_panels, alignment=Qt.AlignmentFlag.AlignTop)
            self.layout.addStretch()
            
            self.local_remote_refresh = QPushButton('Compare LOCAL to REMOTE', clicked=self.refresh_local_and_remote)
            self.local_remote_refresh.setStyleSheet(constants.LEFT_PANEL_CLOSE_ALL_WINDOWS_STYLE)
            self.local_remote_refresh.setFixedHeight(50)
            self.layout.addWidget(self.local_remote_refresh, alignment=Qt.AlignmentFlag.AlignBottom)
            
            self.setLayout(self.layout)
            return None
        
        else:
            if does_object_exist_in_s3_bucket(AllObjectAccess.user_info['user_AWS_ACCESS_KEY_ID'],
                                          AllObjectAccess.user_info['user_AWS_SECRET_ACCESS_KEY'],
                                          AllObjectAccess.user_info['user_AWS_BUCKET_NAME'], 
                                          str(self.project_name + '/project_image.jpg')):
                get_rmt_object_to_loc(AllObjectAccess.user_info['user_AWS_ACCESS_KEY_ID'],
                                      AllObjectAccess.user_info['user_AWS_SECRET_ACCESS_KEY'],
                                      AllObjectAccess.user_info['user_AWS_BUCKET_NAME'], 
                                      str(self.project_name + '/project_image.jpg'),
                                      './.project_image.jpg')        
                self.right_panel_line_1_object.user_pixmap = QPixmap('./.project_image.jpg')
                self.right_panel_line_1_object.user_image.setPixmap(self.right_panel_line_1_object.user_pixmap)
                self.right_panel_line_1_object.user_image.show()
                
            else:
                self.right_panel_line_1_object.user_pixmap = QPixmap()
                self.right_panel_line_1_object.user_image.setPixmap(self.right_panel_line_1_object.user_pixmap)
                self.right_panel_line_1_object.user_image.hide()
                
            self.right_panel_line_1_object.user_image.setPixmap(self.right_panel_line_1_object.user_pixmap)
            self.right_panel_line_1_object.project_name_label.setText('Project: ' + self.project_name)
            self.right_panel_line_1_object.project_name = self.project_name
            self.right_panel_line_1_object.user_name.setText('Owner: ' + AllObjectAccess.user_info['first_name'] + ' ' + AllObjectAccess.user_info['last_name'] + ' [' + AllObjectAccess.user_info['email'] + ']')
            self.right_panel_line_1_object.show()
            
            self.cfg_data = dict()
            with open('./config.json', 'r') as config_file:
                self.cfg_data = json.load(config_file)
            
            self.left_panel_file_dir_1_object.dirModel.setRootPath('')
            self.left_panel_file_dir_1_object.dirModel.setRootPath(self.cfg_data['projects_directory'])
            self.left_panel_file_dir_1_object.treeview.setModel(self.left_panel_file_dir_1_object.dirModel)
            self.local_folder_last_modified = get_last_modified_time_for_local_project(self.cfg_data['projects_directory'] + '/' + self.project_name)
            self.local_last_modified_msg = 'Last updated ' + self.local_folder_last_modified
            self.right_panel_info_panels_object.left_panel.update_info_label.setText(self.local_last_modified_msg)
            self.remote_folder_last_modified = get_last_modified_time_for_remote_project(AllObjectAccess.user_info['user_AWS_ACCESS_KEY_ID'], 
                                                                                  AllObjectAccess.user_info['user_AWS_SECRET_ACCESS_KEY'], 
                                                                                  AllObjectAccess.user_info['user_AWS_BUCKET_NAME'], 
                                                                                  self.project_name)
            self.remote_last_modified_msg = 'Last updated ' + self.remote_folder_last_modified
            self.right_panel_info_panels_object.right_panel.update_info_label.setText(self.remote_last_modified_msg)
            self.right_panel_info_panels_object.left_panel.current_project_path = current_project_path
            self.right_panel_info_panels_object.right_panel.current_project_path = current_project_path
            self.right_panel_info_panels_object.show()
            return None

    def refresh_local_and_remote(self):
    
        self.cfg_data = dict()
        with open('./config.json', 'r') as config_file:
            self.cfg_data = json.load(config_file)
        
        local_index = dict()
        
        for path, subdirs, files in os.walk(self.current_project_path):
            for name in files:
                filepath = os.path.join(path, name)
                sha256 = create_sha256_hash_for_file(filepath)
                object_name = filepath.replace(self.cfg_data['projects_directory'] + '/', '')
                local_index[object_name] = {
                                            "last_modified_at": int(os.path.getmtime(filepath)),
                                            "sha256": sha256
                                            }
        
        # print('LOCAL')
        # print(json.dumps(local_index, sort_keys=True, indent=4))
        # print()
        
        remote_index = dict()
        
        all_remote_prj_files = get_rmt_project_object_versions(AllObjectAccess.user_info['user_AWS_ACCESS_KEY_ID'],
                                           AllObjectAccess.user_info['user_AWS_SECRET_ACCESS_KEY'], 
                                           AllObjectAccess.user_info['user_AWS_BUCKET_NAME'],
                                           self.project_name)
        
        object_list = []
        
        for remote_file in all_remote_prj_files:
            if remote_file['Key'] == self.project_name + '/':
                pass
            else:
                if remote_file['IsLatest'] == True:
                    object_list.append(remote_file)
                
        for obj in object_list:
            sha256 = get_remote_object_metadata(AllObjectAccess.user_info['user_AWS_ACCESS_KEY_ID'],
                                       AllObjectAccess.user_info['user_AWS_SECRET_ACCESS_KEY'],
                                       AllObjectAccess.user_info['user_AWS_BUCKET_NAME'], 
                                       obj['Key'])
            remote_index[obj['Key']] = {
                                       "last_modified_at": int(parser.parse(str(obj['LastModified'])).timestamp()),
                                       "sha256": sha256
                                       }
        
        # print('REMOTE')
        # print(json.dumps(remote_index, sort_keys=True, indent=4, default=str))
        # print()
        
        files_ready_to_upload = []
        
        for local_file in list(local_index.keys()):
            if local_file not in list(remote_index.keys()):
                files_ready_to_upload.append(local_file)
            else:
                if local_index[local_file]["sha256"] != remote_index[local_file]["sha256"]:
                    if local_index[local_file]["last_modified_at"] > remote_index[local_file]["last_modified_at"]:
                        files_ready_to_upload.append(local_file)
                    else:
                        pass
                else:
                    pass
                    
        files_ready_to_download = []
        
        for remote_file in list(remote_index.keys()):
            if remote_file not in list(local_index.keys()):
                files_ready_to_download.append(remote_file)
            else:
                if remote_index[remote_file]["sha256"] != local_index[remote_file]["sha256"]:
                    if remote_index[remote_file]["last_modified_at"] > local_index[remote_file]["last_modified_at"]:
                        files_ready_to_download.append(remote_file)
                    else:
                        pass
                else:
                    pass
        
        print('Files Ready to Upload   ->', files_ready_to_upload)  
        print('Files Ready to Download ->', files_ready_to_download)
        print()

        for obj in AllObjectAccess.all_objects:
            if obj.class_name == 'LeftPanel_Info':
                self.left_panel_info_object = obj
            if obj.class_name == 'RightPanel_Info':
                self.right_panel_info_object = obj

        if not files_ready_to_upload and not files_ready_to_download:
            self.left_panel_info_object.label.setStyleSheet('font-size: 18px; font-weight: 900; color: #1AA260;') 
            self.left_panel_info_object.label.setText(' Up to date')
            ICON_left = 'ei.ok-sign'
            label_icon_left = qta.icon(ICON_left, color='#1AA260')
            self.left_panel_info_object.label.setIcon(label_icon_left)
            self.left_panel_info_object.label.setIconSize(QSize(30, 30))
            
            self.right_panel_info_object.label.setStyleSheet('font-size: 18px; font-weight: 900; color: #1AA260;')
            self.right_panel_info_object.label.setText(' Up to date')
            ICON_right = 'ei.ok-sign'
            label_icon_right = qta.icon(ICON_right, color='#1AA260')
            self.right_panel_info_object.label.setIcon(label_icon_right)
            self.right_panel_info_object.label.setIconSize(QSize(30, 30))
        
        elif files_ready_to_upload and not files_ready_to_download:
            number_files_ready_to_upload = len(files_ready_to_upload)
            self.left_panel_info_object.label.setStyleSheet('font-size: 18px; font-weight: 900; color: #FF69B4;') 
            self.left_panel_info_object.label.setText(f' {number_files_ready_to_upload} Files ready to upload')
            ICON_left = 'fa.cloud-upload'
            label_icon_left = qta.icon(ICON_left, color='#FF69B4')
            self.left_panel_info_object.label.setIcon(label_icon_left)
            self.left_panel_info_object.label.setIconSize(QSize(30, 30))
            
            self.right_panel_info_object.label.setStyleSheet('font-size: 18px; font-weight: 900; color: #1AA260;')
            self.right_panel_info_object.label.setText(' Up to date')
            ICON_right = 'ei.ok-sign'
            label_icon_right = qta.icon(ICON_right, color='#1AA260')
            self.right_panel_info_object.label.setIcon(label_icon_right)
            self.right_panel_info_object.label.setIconSize(QSize(30, 30))
      
        elif not files_ready_to_upload and files_ready_to_download:
            self.left_panel_info_object.label.setStyleSheet('font-size: 18px; font-weight: 900; color: #1AA260;') 
            self.left_panel_info_object.label.setText(' Up to date')
            ICON_left = 'ei.ok-sign'
            label_icon_left = qta.icon(ICON_left, color='#1AA260')
            self.left_panel_info_object.label.setIcon(label_icon_left)
            self.left_panel_info_object.label.setIconSize(QSize(30, 30))
            
            number_files_ready_to_download = len(files_ready_to_download)
            self.right_panel_info_object.label.setStyleSheet('font-size: 18px; font-weight: 900; color: #FF69B4;')
            self.right_panel_info_object.label.setText(f' {number_files_ready_to_download} Files ready to download')
            ICON_right = 'fa.cloud-download'
            label_icon_right = qta.icon(ICON_right, color='#FF69B4')
            self.right_panel_info_object.label.setIcon(label_icon_right)
            self.right_panel_info_object.label.setIconSize(QSize(30, 30))
       
        elif files_ready_to_upload and files_ready_to_download:
            number_files_ready_to_upload = len(files_ready_to_upload)
            self.left_panel_info_object.label.setStyleSheet('font-size: 18px; font-weight: 900; color: #FF69B4;') 
            self.left_panel_info_object.label.setText(f' {number_files_ready_to_upload} Files ready to upload')
            ICON_left = 'fa.cloud-upload'
            label_icon_left = qta.icon(ICON_left, color='#FF69B4')
            self.left_panel_info_object.label.setIcon(label_icon_left)
            self.left_panel_info_object.label.setIconSize(QSize(30, 30))
            
            number_files_ready_to_download = len(files_ready_to_download)
            self.right_panel_info_object.label.setStyleSheet('font-size: 18px; font-weight: 900; color: #FF69B4;')
            self.right_panel_info_object.label.setText(f' {number_files_ready_to_download} Files ready to download')
            ICON_right = 'fa.cloud-download'
            label_icon_right = qta.icon(ICON_right, color='#FF69B4')
            self.right_panel_info_object.label.setIcon(label_icon_right)
            self.right_panel_info_object.label.setIconSize(QSize(30, 30))
        
        else:
            pass
        
        return None
             

class RightPanelLine1(QWidget, AllObjectAccess):
    def __init__(self, project_name):
        super(RightPanelLine1, self).__init__()
        self.class_name = 'RightPanelLine1'
        self.project_name = project_name
        self.layout = QGridLayout()
        self.user_image = QLabel()
        
        if does_object_exist_in_s3_bucket(AllObjectAccess.user_info['user_AWS_ACCESS_KEY_ID'],
                                          AllObjectAccess.user_info['user_AWS_SECRET_ACCESS_KEY'],
                                          AllObjectAccess.user_info['user_AWS_BUCKET_NAME'], 
                                          str(self.project_name + '/project_image.jpg')):
            get_rmt_object_to_loc(AllObjectAccess.user_info['user_AWS_ACCESS_KEY_ID'],
                                  AllObjectAccess.user_info['user_AWS_SECRET_ACCESS_KEY'],
                                  AllObjectAccess.user_info['user_AWS_BUCKET_NAME'], 
                                  str(self.project_name + '/project_image.jpg'),
                                  './.project_image.jpg')        
            self.user_pixmap = QPixmap('./.project_image.jpg')
            self.user_image.setPixmap(self.user_pixmap)
            self.user_image.show()
      
        else:
            self.user_pixmap = QPixmap()
            self.user_image.setPixmap(self.user_pixmap)
            self.user_image.hide()
            
        self.project_name_label = QLabel('Project: ' + self.project_name)
        self.project_name_label.setStyleSheet(constants.RIGHT_PANEL_LINE_1_PROJECT_NAME_STYLE)
        self.project_name_label.setAlignment(Qt.AlignLeft)
        self.user_name = QLabel('Owner: ' + AllObjectAccess.user_info['first_name'] + ' ' + AllObjectAccess.user_info['last_name'] + ' [' + AllObjectAccess.user_info['email'] + ']')
        self.user_name.setStyleSheet(constants.RIGHT_PANEL_LINE_1_USER_NAME_STYLE)
        self.user_name.setAlignment(Qt.AlignLeft)
        self.project_users_info = QPushButton(' 7', clicked=self.project_info)
        self.project_users_info.setStyleSheet(constants.RIGHT_PANEL_LINE_1_SETTINGS_STYLE)
        self.project_users_info.setFixedSize(QSize(100, 50))
        self.project_users_info_icon = qta.icon(constants.NUMBER_OF_USERS_ICON, color='#000000')
        self.project_users_info.setIcon(self.project_users_info_icon)
        self.project_users_info.setIconSize(QSize(40, 40))
        self.add_users = QPushButton('Add Users', clicked=self.add_users_to_project)
        self.add_users.setStyleSheet("QPushButton { font-size: 14px; background-color: transparent; border: 0px }")
        self.add_users.setFixedSize(QSize(125, 50))
        self.add_users_icon = qta.icon(constants.ADD_USERS_ICON, color='#000000')
        self.add_users.setIcon(self.add_users_icon)
        self.add_users.setIconSize(QSize(40, 40))
        self.layout.addWidget(self.user_image, 0, 0, 2, 1, alignment=(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignAbsolute | Qt.AlignmentFlag.AlignTop))
        self.layout.addWidget(self.project_name_label, 0, 1, alignment=(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignAbsolute | Qt.AlignmentFlag.AlignTop))
        self.layout.addWidget(self.user_name, 1, 1, alignment=(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignAbsolute | Qt.AlignmentFlag.AlignTop))
        self.layout.addWidget(self.project_users_info, 0, 2, alignment=(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop))
        self.layout.addWidget(self.add_users, 1, 2, alignment=(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop))
        self.layout.setRowStretch(1, 1)
        self.layout.setColumnStretch(1, 1)
        self.setLayout(self.layout)
        return None
    
    def get_project_info(self):
    
        AllObjectAccess.user_info = get_item_from_DynamoDB_table(constants.AWS_DYNAMODB_TABLE, AllObjectAccess.user_info['email'])
        
        for prj, prj_info in AllObjectAccess.user_info['projects'].items():
            if prj == self.project_name:
                print(prj_info)
        
        return None

    def project_info(self):
        self.get_project_info()
        print()
        return None
        
    def add_users_to_project(self):
        AllObjectAccess.user_info = get_item_from_DynamoDB_table(constants.AWS_DYNAMODB_TABLE, AllObjectAccess.user_info['email'])
        print('Add a user to the project...')
        print('Project Name: ', self.project_name)
        print('Project Owner:', AllObjectAccess.user_info['projects'][self.project_name]
        print('Remote S3 Bucket:', 
        return None 


class BasePanel(QWidget):
    """This is more or less abstract, subclass it for 'panels' in the main UI"""
    def __init__(self, parent=None):
        super(BasePanel, self).__init__(parent)
        self.frame_layout = QVBoxLayout()
        self.frame_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.frame_layout)
        self.frame = QFrame()
        self.frame.setObjectName("base_frame")
        self.frame.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        self.frame.setLineWidth(1)
        self.frame_layout.addWidget(self.frame)
        self.base_layout = QVBoxLayout()
        self.frame.setLayout(self.base_layout)
        self.focus_in_color = "#FE1493"
        self.focus_out_color = "#FFFFFF"  # --> that blue #3BB9FF
        self.frame.setStyleSheet(f"background-color: #504A4B; border-radius: 4px; border: 0px solid {self.focus_out_color};")
        self.installEventFilter(self) # this will catch focus events'

    def eventFilter(self, object, event):
        if event.type() == QEvent.Type.FocusIn:
            self.frame.setStyleSheet(f"background-color: #504A4B; border-radius: 4px; border: 0px solid {self.focus_in_color};")
        elif event.type() == QEvent.Type.FocusOut:
            self.frame.setStyleSheet(f"background-color: #504A4B; border-radius: 4px; border: 0px solid {self.focus_out_color};")
        return False # passes this event to the child, i.e. does not block it from the child widgets

    def showEvent(self, event):
        super(BasePanel, self).showEvent(event)
        # this will isntal the focus in/out event filter in all children of the panel
        for widget in self.findChildren(QWidget):
            widget.installEventFilter(self)


class HorizontalLine(QFrame):
    def __init__(self):
        super(HorizontalLine, self).__init__()
        self.setFrameShape(QFrame.Shape.HLine)
        self.setFrameShadow(QFrame.Shadow.Raised)
        self.setFixedHeight(1)
        self.setStyleSheet('background-color: #B6B6B4; padding-top: 18px; padding-bottom: 18px; padding-left: 18px; padding-right: 18px;')
        return None


class LeftPanel_Info(BasePanel, AllObjectAccess):
    def __init__(self, current_project_path, parent=None):
        super(LeftPanel_Info, self).__init__(parent)
        self.class_name = 'LeftPanel_Info'
        self.current_project_path = current_project_path
        self.project_name = self.current_project_path.split('/')[-1]
        self.title = QLabel("LOCAL FOLDER")
        self.title.setStyleSheet('font-size: 24px; font-weight: 900; color: #B6B6B4; border-radius: 0px; border: 0px solid #000000;')
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.base_layout.addWidget(self.title)
        self.font_spaced = self.title.font()
        self.font_spaced.setLetterSpacing(QFont.PercentageSpacing, 150)
        self.title.setFont(self.font_spaced)
        self.hline = HorizontalLine()
        self.base_layout.addWidget(self.hline)
        self.label = QPushButton(' Up to date')
        self.label.setStyleSheet(constants.LEFT_PANEL_LINE_1_SETTINGS_STYLE)
        self.label.setStyleSheet('font-size: 18px; font-weight: 900; color: #1AA260;')
        self.label.setFixedSize(QSize(300, 75))
        self.ICON_1 = 'ei.ok-sign'
        self.label_icon = qta.icon(self.ICON_1, color='#1AA260')
        self.label.setIcon(self.label_icon)
        self.label.setIconSize(QSize(30, 30))
        self.base_layout.addWidget(self.label, alignment=(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignBottom))
        self.local_icon = QPushButton('')
        self.local_icon.setStyleSheet(constants.LEFT_PANEL_LINE_1_SETTINGS_STYLE)
        self.local_icon.setFixedSize(QSize(150, 150))
        self.ICON_1 = 'ph.files-bold'
        self.ICON_2 = 'fa5s.folder-open'
        self.local_icon_icon = qta.icon(self.ICON_1, self.ICON_2, options = [
                {'scale_factor': 0.8, 'offset': (0.0, 0.0), 
                'color': 'white', 'opacity': 1.0}, 
                {'scale_factor': 0.8, 'offset': (0.0, 0.25), 
                'color': 'white', 'opacity': 0.75}])
        self.local_icon.setIcon(self.local_icon_icon)
        self.local_icon.setIconSize(QSize(150, 150))
        self.base_layout.addWidget(self.local_icon, alignment=(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignCenter))
        self.base_layout.addStretch()
        
        for obj in AllObjectAccess.all_objects:
            if obj.class_name == 'LeftPanelFileDir1':
                self.left_panel_file_dir_1_object = obj
                
        self.cfg_data = dict()
        with open('./config.json', 'r') as config_file:
            self.cfg_data = json.load(config_file)

        self.left_panel_file_dir_1_object.dirModel.setRootPath('')
        self.left_panel_file_dir_1_object.dirModel.setRootPath(self.cfg_data['projects_directory'])
        self.left_panel_file_dir_1_object.treeview.setModel(self.left_panel_file_dir_1_object.dirModel)
        self.local_folder_last_modified = get_last_modified_time_for_local_project(self.cfg_data['projects_directory'] + '/' + self.project_name)
        self.local_last_modified_msg = 'Last updated ' + self.local_folder_last_modified
        self.update_info_label = QLabel(self.local_last_modified_msg)
        self.update_info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.update_info_label.setWordWrap(True)
        self.update_info_label.setStyleSheet('font-size: 12px; font-weight: 700; color: #FFFFFF;')
        self.update_info_label.setFixedSize(QSize(275, 50))
        self.base_layout.addWidget(self.update_info_label, alignment=(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignBottom))
        self.base_layout.addStretch()
        self.open_folder_button = QPushButton('OPEN FOLDER', clicked=self.open_local_project)
        self.open_folder_button.setFont(self.font_spaced)
        self.open_folder_button.setStyleSheet('font-size: 18px; font-weight: 900; color: #B6B6B4; border-radius: 0px; border: 0px solid #000000; background-color: #660000;')
        self.open_folder_button.setFixedSize(QSize(275, 50))
        self.base_layout.addWidget(self.open_folder_button, alignment=(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignBottom))
    
    def open_local_project(self):
        self.local_project_folder = LocalProjectFolder(self.current_project_path)
        self.local_project_folder.show()
        return None


class RightPanel_Info(BasePanel, AllObjectAccess):
    def __init__(self, current_project_path, parent=None):
        super(RightPanel_Info, self).__init__(parent)
        self.class_name = 'RightPanel_Info'
        self.current_project_path = current_project_path
        self.project_name = self.current_project_path.split('/')[-1]
        self.title = QLabel("WORKBENCH")
        self.title.setStyleSheet('font-size: 24px; font-weight: 900; color: #B6B6B4; border-radius: 0px; border: 0px solid #000000;')
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.base_layout.addWidget(self.title)
        self.font_spaced = self.title.font()
        self.font_spaced.setLetterSpacing(QFont.PercentageSpacing, 150)
        self.title.setFont(self.font_spaced)
        self.hline = HorizontalLine()
        self.base_layout.addWidget(self.hline)
        self.label = QPushButton(' Up to date')
        self.label.setStyleSheet(constants.LEFT_PANEL_LINE_1_SETTINGS_STYLE)
        self.label.setStyleSheet('font-size: 18px; font-weight: 900; color: #1AA260;')
        self.label.setFixedSize(QSize(300, 75))
        self.ICON_1 = 'ei.ok-sign'
        self.label_icon = qta.icon(self.ICON_1, color='#1AA260')
        self.label.setIcon(self.label_icon)
        self.label.setIconSize(QSize(30, 30))
        self.base_layout.addWidget(self.label, alignment=(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignBottom))
        self.local_icon = QPushButton('')
        self.local_icon.setStyleSheet(constants.LEFT_PANEL_LINE_1_SETTINGS_STYLE)
        self.local_icon.setFixedSize(QSize(150, 150))
        self.ICON_1 = 'ph.files-bold'
        self.ICON_2 = 'mdi.cloud'
        self.local_icon_icon = qta.icon(self.ICON_1, self.ICON_2, options = [
                {'scale_factor': 0.8, 'offset': (0.0, 0.0), 
                'color': 'white', 'opacity': 1.0}, 
                {'scale_factor': 0.8, 'offset': (0.0, 0.25), 
                'color': 'white', 'opacity': 0.75}])
        self.local_icon.setIcon(self.local_icon_icon)
        self.local_icon.setIconSize(QSize(150, 150))
        self.base_layout.addWidget(self.local_icon, alignment=(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignCenter))
        self.base_layout.addStretch()
        
        for obj in AllObjectAccess.all_objects:
            if obj.class_name == 'LeftPanelFileDir1':
                self.left_panel_file_dir_1_object = obj
                
        self.cfg_data = dict()
        with open('./config.json', 'r') as config_file:
            self.cfg_data = json.load(config_file)

        self.left_panel_file_dir_1_object.dirModel.setRootPath('')
        self.left_panel_file_dir_1_object.dirModel.setRootPath(self.cfg_data['projects_directory'])
        self.left_panel_file_dir_1_object.treeview.setModel(self.left_panel_file_dir_1_object.dirModel)
        self.remote_folder_last_modified = get_last_modified_time_for_remote_project(AllObjectAccess.user_info['user_AWS_ACCESS_KEY_ID'], 
                                                                                  AllObjectAccess.user_info['user_AWS_SECRET_ACCESS_KEY'], 
                                                                                  AllObjectAccess.user_info['user_AWS_BUCKET_NAME'], 
                                                                                  self.project_name)
        self.remote_last_modified_msg = 'Last updated ' + self.remote_folder_last_modified
        self.update_info_label = QLabel(self.remote_last_modified_msg)
        self.update_info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.update_info_label.setWordWrap(True)
        self.update_info_label.setStyleSheet('font-size: 12px; font-weight: 700; color: #FFFFFF;')
        self.update_info_label.setFixedSize(QSize(275, 50))
        self.base_layout.addWidget(self.update_info_label, alignment=(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignBottom))
        self.base_layout.addStretch()
        self.open_project_button = QPushButton('OPEN PROJECT', clicked=self.open_remote_project)
        self.open_project_button.setFont(self.font_spaced)
        self.open_project_button.setStyleSheet('font-size: 18px; font-weight: 900; color: #B6B6B4; border-radius: 0px; border: 0px solid #000000; background-color: #660000;')
        self.open_project_button.setFixedSize(QSize(275, 50))
        self.base_layout.addWidget(self.open_project_button, alignment=(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignBottom))

    def open_remote_project(self):
        self.remote_project_folder = RemoteProjectFolder(self.current_project_path)
        self.remote_project_folder.show()
        return None
                
    def get_project_info(self):
        
        for prj in AllObjectAccess.user_info['projects']['owner']:
            if self.project_name == prj['folder']:
                return prj['folder']
        
        for prj in AllObjectAccess.user_info['projects']['creator']:
            if self.project_name == prj['folder']:
                return prj['folder']
        
        for prj in AllObjectAccess.user_info['projects']['viewer']:
            if self.project_name == prj['folder']:
                return prj['folder']
                
        return dict()
                  

class RightPanelInfoPanels(QWidget, AllObjectAccess):
    def __init__(self, current_project_path):
        super(RightPanelInfoPanels, self).__init__()
        self.class_name = 'RightPanelInfoPanels'
        self.current_project_path = current_project_path
        self.layout = QHBoxLayout()
        self.left_panel = LeftPanel_Info(self.current_project_path)
        self.layout.addWidget(self.left_panel)
        self.test = QPushButton()
        self.test.setStyleSheet('background-color: transparent; border: 0px')
        self.test.setFixedSize(QSize(75, 75))
        self.test_icon = qta.icon('fa5s.ellipsis-h', color='#FFFFFF')
        self.test.setIcon(self.test_icon)
        self.test.setIconSize(QSize(75, 75))
        self.layout.addWidget(self.test)
        self.right_panel = RightPanel_Info(self.current_project_path)
        self.layout.addWidget(self.right_panel)
        self.setLayout(self.layout)
        return None


FSMItemOrNone = Union["_FileSystemModelLiteItem", None]


class _FileSystemModelLiteItem(object):
    """Represents a single node (drive, folder or file) in the tree"""

    def __init__(
        self,
        data: List[Any],
        icon=QFileIconProvider.IconType.Computer,
        parent: FSMItemOrNone = None,
    ):
        self._data: List[Any] = data
        self._icon = icon
        self._parent: _FileSystemModelLiteItem = parent
        self.child_items: List[_FileSystemModelLiteItem] = []
        self.is_checkable = True

    def append_child(self, child: "_FileSystemModelLiteItem"):
        self.child_items.append(child)

    def child(self, row: int) -> FSMItemOrNone:
        try:
            return self.child_items[row]
        except IndexError:
            return None

    def child_count(self) -> int:
        return len(self.child_items)

    def column_count(self) -> int:
        return len(self._data)

    def data(self, column: int) -> Any:
        try:
            return self._data[column]
        except IndexError:
            return None

    def icon(self):
        return self._icon

    def row(self) -> int:
        if self._parent:
            return self._parent.child_items.index(self)
        return 0

    def parent_item(self) -> FSMItemOrNone:
        return self._parent


class FileSystemModelLiteLocal(QAbstractItemModel, AllObjectAccess):
    def __init__(self, file_list: List[str], parent=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.class_name = 'FileSystemModelLiteLocal'
        self._icon_provider = QFileIconProvider()

        self._root_item = _FileSystemModelLiteItem(
            ["Filename", "Relative Path", "Size (bytes)", "Modified (local time)"]
        )
        self._setup_model_data(file_list, self._root_item)
        self.checks = {}
        self.upload_files = []
        
    def reset_model_data(self, file_list: List[str]):
        self.beginResetModel()
        del self._root_item
        self._root_item = _FileSystemModelLiteItem(
            ["Filename", "Relative Path", "Size (bytes)", "Modified (local time)"]
        )
        self._setup_model_data(file_list, self._root_item)
        self.endResetModel()
        return None

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid():
            return None

        item: _FileSystemModelLiteItem = index.internalPointer()
        col = index.column()
        
        if role == Qt.CheckStateRole and col == 1 and item.is_checkable:
            return self.checks.get(QPersistentModelIndex(index), Qt.Unchecked)
        
        if role == Qt.ItemDataRole.DisplayRole:
            return item.data(index.column())
        elif index.column() == 0 and role == Qt.ItemDataRole.DecorationRole:
            return self._icon_provider.icon(item.icon())
            
        return None

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        if not index.isValid():
            return False
        
        if role == Qt.ItemDataRole.CheckStateRole:
            if value == Qt.CheckState.Unchecked.value:
                if index.data() in self.upload_files:
                    self.upload_files = [x for x in self.upload_files if x != index.data()]
                    self.upload_files.sort()
            elif value == Qt.CheckState.Checked.value:
                if index.data() not in self.upload_files:
                    self.upload_files.append(index.data())
                    self.upload_files.sort()
            else:
                pass
                           
        if role == Qt.ItemDataRole.CheckStateRole:
            self.checks[QPersistentModelIndex(index)] = value
            return True
            
        return False

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        flags = super().flags(index)
        item = index.internalPointer()
        if item and item.is_checkable:
            flags |= Qt.ItemIsUserCheckable
        return flags

    def headerData(
        self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole
    ) -> Any:
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self._root_item.data(section)
        return None

    def index(
        self, row: int, column: int, parent: QModelIndex = QModelIndex()
    ) -> QModelIndex:
        if not self.hasIndex(row, column, parent):
            return QModelIndex()

        if not parent.isValid():
            parent_item = self._root_item
        else:
            parent_item = parent.internalPointer()

        child_item = parent_item.child(row)
        if child_item:
            return self.createIndex(row, column, child_item)
        return QModelIndex()

    def parent(self, index: QModelIndex) -> QModelIndex:
        if not index.isValid():
            return QModelIndex()

        child_item: _FileSystemModelLiteItem = index.internalPointer()
        parent_item: FSMItemOrNone = child_item.parent_item()

        if parent_item == self._root_item:
            return QModelIndex()

        return self.createIndex(parent_item.row(), 0, parent_item)

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.column() > 0:
            return 0

        if not parent.isValid():
            parent_item = self._root_item
        else:
            parent_item = parent.internalPointer()

        return parent_item.child_count()

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return parent.internalPointer().column_count()
        return self._root_item.column_count()

    def _setup_model_data(
        self, file_list: List[str], parent: "_FileSystemModelLiteItem"
    ):
        def _add_to_tree(_file_record, _parent: "_FileSystemModelLiteItem", root=False):
            item_name = _file_record["bits"].pop(0)
            for child in _parent.child_items:
                if item_name == child.data(0):
                    item = child
                    break
            else:
                data = [item_name, "", "", ""]
                if root:
                    icon = QFileIconProvider.IconType.Desktop  # IconType.File was Computer
                elif len(_file_record["bits"]) == 0:
                    icon = QFileIconProvider.IconType.File
                    data = [
                        item_name,
                        _file_record["path"],
                        _file_record["size"],
                        _file_record["modified_at"]
                    ]
                else:
                    icon = QFileIconProvider.IconType.Folder

                item = _FileSystemModelLiteItem(data, icon=icon, parent=_parent)
                _parent.append_child(item)

            if len(_file_record["bits"]):
                _add_to_tree(_file_record, item)

        for file in file_list:
            file_record = {
                "path": file["Key"],
                "size": file['Size'],
                "modified_at": str(file['LastModified']),
            }

            drive = True
            if "\\" in file['Key']:
                file['Key'] = posixpath.join(*file['Key'].split("\\"))
            bits = file['Key'].split("/")
            if len(bits) > 1 and bits[0] == "":
                bits[0] = "/"
                drive = False

            file_record["bits"] = bits
            _add_to_tree(file_record, parent, drive)


class FileSystemModelLiteRemote(QAbstractItemModel, AllObjectAccess):
    def __init__(self, file_list: List[str], parent=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.class_name = 'FileSystemModelLiteLocal'
        self._icon_provider = QFileIconProvider()

        self._root_item = _FileSystemModelLiteItem(
            ["Filename", "Relative Path", "Size (bytes)", "Modified (utc time)"]
        )
        self._setup_model_data(file_list, self._root_item)
        self.checks = {}
        self.upload_files = []
        
    def reset_model_data(self, file_list: List[str]):
        self.beginResetModel()
        del self._root_item
        self._root_item = _FileSystemModelLiteItem(
            ["Filename", "Relative Path", "Size (bytes)", "Modified (utc time)"]
        )
        self._setup_model_data(file_list, self._root_item)
        self.endResetModel()
        return None

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid():
            return None

        item: _FileSystemModelLiteItem = index.internalPointer()
        col = index.column()
        
        if role == Qt.CheckStateRole and col == 1 and item.is_checkable:
            return self.checks.get(QPersistentModelIndex(index), Qt.Unchecked)
        
        if role == Qt.ItemDataRole.DisplayRole:
            return item.data(index.column())
        elif index.column() == 0 and role == Qt.ItemDataRole.DecorationRole:
            return self._icon_provider.icon(item.icon())
            
        return None

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        if not index.isValid():
            return False
        
        if role == Qt.ItemDataRole.CheckStateRole:
            if value == Qt.CheckState.Unchecked.value:
                if index.data() in self.upload_files:
                    self.upload_files = [x for x in self.upload_files if x != index.data()]
                    self.upload_files.sort()
            elif value == Qt.CheckState.Checked.value:
                if index.data() not in self.upload_files:
                    self.upload_files.append(index.data())
                    self.upload_files.sort()
            else:
                pass
                           
        if role == Qt.ItemDataRole.CheckStateRole:
            self.checks[QPersistentModelIndex(index)] = value
            return True
            
        return False

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        flags = super().flags(index)
        item = index.internalPointer()
        if item and item.is_checkable:
            flags |= Qt.ItemIsUserCheckable
        return flags

    def headerData(
        self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole
    ) -> Any:
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self._root_item.data(section)
        return None

    def index(
        self, row: int, column: int, parent: QModelIndex = QModelIndex()
    ) -> QModelIndex:
        if not self.hasIndex(row, column, parent):
            return QModelIndex()

        if not parent.isValid():
            parent_item = self._root_item
        else:
            parent_item = parent.internalPointer()

        child_item = parent_item.child(row)
        if child_item:
            return self.createIndex(row, column, child_item)
        return QModelIndex()

    def parent(self, index: QModelIndex) -> QModelIndex:
        if not index.isValid():
            return QModelIndex()

        child_item: _FileSystemModelLiteItem = index.internalPointer()
        parent_item: FSMItemOrNone = child_item.parent_item()

        if parent_item == self._root_item:
            return QModelIndex()

        return self.createIndex(parent_item.row(), 0, parent_item)

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.column() > 0:
            return 0

        if not parent.isValid():
            parent_item = self._root_item
        else:
            parent_item = parent.internalPointer()

        return parent_item.child_count()

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return parent.internalPointer().column_count()
        return self._root_item.column_count()

    def _setup_model_data(
        self, file_list: List[str], parent: "_FileSystemModelLiteItem"
    ):
        def _add_to_tree(_file_record, _parent: "_FileSystemModelLiteItem", root=False):
            item_name = _file_record["bits"].pop(0)
            for child in _parent.child_items:
                if item_name == child.data(0):
                    item = child
                    break
            else:
                data = [item_name, "", "", ""]
                if root:
                    icon = QFileIconProvider.IconType.Desktop  # IconType.File was Computer
                elif len(_file_record["bits"]) == 0:
                    icon = QFileIconProvider.IconType.File
                    data = [
                        item_name,
                        _file_record["path"],
                        _file_record["size"],
                        _file_record["modified_at"]
                    ]
                else:
                    icon = QFileIconProvider.IconType.Folder

                item = _FileSystemModelLiteItem(data, icon=icon, parent=_parent)
                _parent.append_child(item)

            if len(_file_record["bits"]):
                _add_to_tree(_file_record, item)

        for file in file_list:
            file_record = {
                "path": file["Key"],
                "size": file['Size'],
                "modified_at": str(file['LastModified']),
            }

            drive = True
            if "\\" in file['Key']:
                file['Key'] = posixpath.join(*file['Key'].split("\\"))
            bits = file['Key'].split("/")
            if len(bits) > 1 and bits[0] == "":
                bits[0] = "/"
                drive = False

            file_record["bits"] = bits
            _add_to_tree(file_record, parent, drive)


class LocalProjectFolder(QWidget, AllObjectAccess):
    def __init__(self, current_project_path):
        super(LocalProjectFolder, self).__init__()
        self.class_name = 'LocalProjectFolder'
        self.current_project_path = current_project_path
        self.current_project = self.current_project_path.split('/')[-1]
        title = 'BigFoot Workbench Project LOCAL: ' + self.current_project
        self.files_to_download = []
        self.setWindowTitle(title)
        self.layout = QVBoxLayout(self)
        
        self.gen_local_file_index = QPushButton('GENERATE LOCAL FILE INDEX', clicked=self.gen_local_index)
        self.layout.addWidget(self.gen_local_file_index, stretch=1)
        
        self.upload_label = QLabel('UPLOAD DOCUMENTATION')
        self.upload_label.setStyleSheet('color: #FFFFFF; font-family: Courier New; font-size: 14px; font-weight: 900;')
        self.layout.addWidget(self.upload_label, alignment=(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom))
        self.upload_comment = QPlainTextEdit()
        self.upload_comment.setStyleSheet(constants.LEFT_PROJECT_OPEN_UPLOAD_COMMENT_STYLE)
        self.upload_comment.setDocumentTitle('')
        self.layout.addWidget(self.upload_comment, stretch=1)
        
        self.sublayout_1 = QHBoxLayout()
        
        self.select_all_button_1 = QPushButton('Select All (not working)')
        self.select_all_button_1.setStyleSheet('background-color: #FFFFFF; font-family: Courier New; font-size: 14px; font-weight: 900;')
        self.sublayout_1.addWidget(self.select_all_button_1, alignment=(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom))
        
        self.upload_button_2 = QPushButton('Upload Selected Files', clicked=self.upload_selected_files)
        self.upload_button_2.setStyleSheet('background-color: #FFFFFF; font-family: Courier New; font-size: 14px; font-weight: 900;')
        self.sublayout_1.addWidget(self.upload_button_2, alignment=(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom))
        
        self.layout.addLayout(self.sublayout_1)
        
        self.cfg_data = dict()
        with open('./config.json', 'r') as config_file:
            self.cfg_data = json.load(config_file)
        
        self.file_list = get_local_project_info(self.cfg_data['projects_directory'], self.current_project)
        
        for f in self.file_list:
            print(f)
        print()
                                     
        self._fileSystemModel = FileSystemModelLiteLocal(self.file_list, self)
        
        self._treeView = QTreeView(self)
        self._treeView.setStyleSheet(constants.LEFT_PANEL_FILE_DIR_STYLE)
        self._treeView.setModel(self._fileSystemModel)
        
        try:
            self.mfs = threading.Thread(target=self.monitor_local_project, args=(), daemon=True)
            self.mfs.start()
        except:
            sys.exit()
        
        self._treeView.setSortingEnabled(True)
        self._treeView.header().setSectionResizeMode(QHeaderView.Stretch)
        self.layout.addWidget(self._treeView, stretch=2)
        
        self.file_upload_status = QStatusBar()
        self.file_upload_status.setStyleSheet('background-color: #FFFFFF; font-family: Courier New; font-size: 12px; font-weight: 900;')
        self.layout.addWidget(self.file_upload_status, stretch=2)
        self.file_upload_status.showMessage('This section can/will be used for file upload status info...') 
        
        self.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, True)
        self.resize(1280, 700)
        return None

    def gen_local_index(self):
        
        local_index = dict()
        
        for path, subdirs, files in os.walk(self.current_project_path):
            for name in files:
                filepath = os.path.join(path, name)
                sha256 = create_md5_sha1_hashes_for_file(filepath)
                object_name = filepath.replace(self.cfg_data['projects_directory'] + '/', '')
                local_index[object_name] = {
                                            "last_modified_at": os.path.getmtime(filepath),
                                            "sha256": sha256
                                            }
        
        print(json.dumps(local_index, sort_keys=True, indent=4))
        
        return None

    def monitor_local_project(self):
    
        self.keep_monitor_active = True
        
        while True:
            tmp_file_list = get_local_project_info(self.cfg_data['projects_directory'], self.current_project)
            if self.file_list != tmp_file_list:
                self.file_list = tmp_file_list
                self._fileSystemModel.reset_model_data(self.file_list)
                self._treeView.update()
                # self._treeView.expandAll() <-- ??? QBasicTimer::start: QBasicTimer can only be used with threads started with QThread
            time.sleep(1)
            if not self.keep_monitor_active:
                break
            
        return None

    def upload_selected_files(self):
        current_utc = int(time.time())
        upload_comment_dynamo_db = AllObjectAccess.user_info['user_AWS_BUCKET_NAME'] + '_' + self.current_project
        user_name = AllObjectAccess.user_info['first_name'] + ' ' + AllObjectAccess.user_info['last_name']
        user_email = AllObjectAccess.user_info['email']
        upload_comment = self.upload_comment.toPlainText()
        
        upload_entry = {
                        "action": 'UPLOAD',
                        "utc_time": str(current_utc),
                        "user_name": user_name,
                        "user_email": user_email,
                        "upload_comment": upload_comment,
                        "files_uploaded": self._fileSystemModel.upload_files
                       }
        
        print(json.dumps(upload_entry, sort_keys=False, indent=4))
        
        time.sleep(3)
        self.upload_comment.clear()
    
        for f in self._fileSystemModel.upload_files:
            sha256 = create_sha256_hash_for_file(self.cfg_data['projects_directory'] + '/' + f)
            
            put_loc_object_to_rmt(AllObjectAccess.user_info['user_AWS_ACCESS_KEY_ID'],
                                  AllObjectAccess.user_info['user_AWS_SECRET_ACCESS_KEY'], 
                                  self.cfg_data['projects_directory'] + '/' + f, 
                                  AllObjectAccess.user_info['user_AWS_BUCKET_NAME'],
                                  f, sha256)

        put_item_to_DynamoDB_table(upload_comment_dynamo_db, upload_entry)
        
        print('Upload done.')

        return None

    def closeEvent(self, event):
            event.accept()
            self.keep_monitor_active = False
            return None

class RemoteProjectFolder(QWidget, AllObjectAccess):
    def __init__(self, current_project_path):
        super(RemoteProjectFolder, self).__init__()
        self.class_name = 'RemoteProjectFolder'
        self.current_project_path = current_project_path
        self.current_project = self.current_project_path.split('/')[-1]
        title = 'BigFoot Workbench Project REMOTE: ' + self.current_project
        self.files_to_download = []
        self.setWindowTitle(title)
        self.layout = QVBoxLayout(self)
        
        self.gen_remote_file_index = QPushButton('GENERATE REMOTE FILE INDEX', clicked=self.gen_remote_index)
        self.layout.addWidget(self.gen_remote_file_index, stretch=1)
        
        self.upload_label = QLabel('This field is not needed')
        self.upload_label.setStyleSheet('color: #FFFFFF; font-family: Courier New; font-size: 14px; font-weight: 900;')
        self.layout.addWidget(self.upload_label, alignment=(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom))
        self.upload_comment = QPlainTextEdit()
        self.upload_comment.setStyleSheet(constants.LEFT_PROJECT_OPEN_UPLOAD_COMMENT_STYLE)
        self.upload_comment.setDocumentTitle('')
        self.layout.addWidget(self.upload_comment, stretch=1)
        
        
        self.sublayout_1 = QHBoxLayout()
        
        self.select_all_button_1 = QPushButton('Select All (not working)')
        self.select_all_button_1.setStyleSheet('background-color: #FFFFFF; font-family: Courier New; font-size: 14px; font-weight: 900;')
        self.sublayout_1.addWidget(self.select_all_button_1, alignment=(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom))
        
        self.upload_button_2 = QPushButton('Download Selected Files', clicked=self.download_selected_files)
        self.upload_button_2.setStyleSheet('background-color: #FFFFFF; font-family: Courier New; font-size: 14px; font-weight: 900;')
        self.sublayout_1.addWidget(self.upload_button_2, alignment=(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom))
        
        self.layout.addLayout(self.sublayout_1)
        
        all_remote_prj_files = get_rmt_project_object_versions(AllObjectAccess.user_info['user_AWS_ACCESS_KEY_ID'],
                                           AllObjectAccess.user_info['user_AWS_SECRET_ACCESS_KEY'], 
                                           AllObjectAccess.user_info['user_AWS_BUCKET_NAME'],
                                           self.current_project)
        
        file_list = []
        
        for remote_file in all_remote_prj_files:
            if remote_file['Key'] == self.current_project + '/':
                pass
            else:
                file_list.append(remote_file)
                                     
        self._fileSystemModel = FileSystemModelLiteRemote(file_list, self)
        self._treeView = QTreeView(self)
        self._treeView.setStyleSheet(constants.RIGHT_PANEL_FILE_DIR_STYLE)
        self._treeView.setModel(self._fileSystemModel)
        self._treeView.setSortingEnabled(True)
        self._treeView.header().setSectionResizeMode(QHeaderView.Stretch)
        self.layout.addWidget(self._treeView, stretch=2)
        
        self.file_upload_status = QStatusBar()
        self.file_upload_status.setStyleSheet('background-color: #FFFFFF; font-family: Courier New; font-size: 12px; font-weight: 900;')
        self.layout.addWidget(self.file_upload_status, stretch=2)
        self.file_upload_status.showMessage('This section can/will be used for file upload status info...') 
        
        self.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, True)
        self.resize(1280, 700)
        return None

    def gen_remote_index(self):
        
        remote_index = dict()
        
        all_remote_prj_files = get_rmt_project_object_versions(AllObjectAccess.user_info['user_AWS_ACCESS_KEY_ID'],
                                           AllObjectAccess.user_info['user_AWS_SECRET_ACCESS_KEY'], 
                                           AllObjectAccess.user_info['user_AWS_BUCKET_NAME'],
                                           self.current_project)
        
        object_list = []
        
        for remote_file in all_remote_prj_files:
            if remote_file['Key'] == self.current_project + '/':
                pass
            else:
                if remote_file['IsLatest'] == True:
                    object_list.append(remote_file)
                
        for obj in object_list:
            sha256 = get_remote_object_metadata(AllObjectAccess.user_info['user_AWS_ACCESS_KEY_ID'],
                                       AllObjectAccess.user_info['user_AWS_SECRET_ACCESS_KEY'],
                                       AllObjectAccess.user_info['user_AWS_BUCKET_NAME'], 
                                       obj['Key'])
            remote_index[obj['Key']] = {
                                        "last_modified_at": obj['LastModified'],
                                        "sha256": sha256
                                       }
        
        return None

    def download_selected_files(self):
        print('Download selected files...')
        return None
        
        
