#!/usr/bin/env python3

black = '#000000'
blue_green = '#7BCCB5'
fluorescent_pink = '#FE1493'
transparent = 'transparent'
white = '#FFFFFF'

# Root access/secret keys apply to top-level/root 'administrator'.
AWS_REGION = 'us-west-2'
AWS_ROOT_ACCESS_KEY_ID = ''
AWS_ROOT_SECRET_ACCESS_KEY = ''
AWS_DYNAMODB_TABLE = 'CAD_user_table'

# <LoginWidget> class constants
LOGIN_WINDOW_TTL = 'BigFoot Login'
LOGIN_MAIN_STYLE = 'background-color: #3D3C38;'
LOGIN_LABEL_STYLE = f'font-weight: 900; color: {white};'
LOGIN_STATUS_STYLE = f'font-family: Courier New; font-size: 12px; font-weight: 900; color: {fluorescent_pink};'
LOGIN_WINDOW_ICON = ''
LOGIN_WINDOW_H = 160
LOGIN_WINDOW_W = 500
LOGIN_DELAY_SEC = 2

# <AppMainWindow> class constants
MAIN_WINDOW_TTL = 'BigFoot Workbench'
MAIN_STYLE = f'background-color: {blue_green}; border:0px solid {black};' 
MAIN_LABEL_STYLE = f'font-weight: 900; color: {white};'
MAIN_STATUS_STYLE = 'font-family: Courier New; font-size: 12px; font-weight: 900; color: {fluorescent_pink};'
MAIN_WINDOW_ICON = ''
MAIN_WINDOW_H = 700
MAIN_WINDOW_W = 1280

# <LeftPanel> class constants
LEFT_PANEL_TTL = ''
LEFT_PANEL_STYLE = f'font-weight: 900; color: {white}; background-color: {fluorescent_pink};'
LEFT_PANEL_STATUS_STYLE = f'font-size: 14px; font-weight: 900; color: {black};'
LEFT_PANEL_WINDOW_ICON = ''
LEFT_PANEL_CLOSE_ALL_WINDOWS_STYLE = f'font-size: 14px; font-weight: 900; color: {fluorescent_pink}; background-color: {white};'
LEFT_PANEL_WINDOW_H = 700
LEFT_PANEL_WINDOW_W = 400

# <LeftPanelLine1> class constants
LEFT_PANEL_LINE_1_USER_IMAGE = '.cow2.jpg'  # <--- convert -resize 65x65 file_1.jpg file_2.jpg
LEFT_PANEL_LINE_1_STYLE = f'font-size: 20px; font-weight: 900; color: {white}; background-color: {blue_green};'
LEFT_PANEL_LINE_1_SETTINGS_ICON = 'ei.cogs'
LEFT_PANEL_LINE_1_SETTINGS_STYLE = 'background-color: transparent; border: 0px'

# <LeftPanel_Line2> class constants
LEFT_PANEL_LINE_2_STYLE = f'font-size: 20px; font-weight: 900; color: {white}; background-color: {blue_green};'
LEFT_PANEL_LINE_2_FOLDER_STYLE = f'background-color: {transparent}; border: 0px'
LEFT_PANEL_LINE_2_FOLDER_CLOSED = 'SP_DirClosedIcon'
LEFT_PANEL_LINE_2_FOLDER_OPEN = 'SP_DirOpenIcon'
LEFT_PANEL_LINE_2_NEW_PROJECT_ICON = 'ei.file-new'

# <CreateNewProject> class constants
CREATE_NEW_PROJECT_WINDOW_TTL = 'BigFoot -- Create New Project'
CREATE_NEW_PROJECT_MAIN_STYLE = 'background-color: #3D3C38;'
CREATE_NEW_PROJECT_LABEL_STYLE = f'font-weight: 900; color: {white};'
CREATE_NEW_PROJECT_STATUS_STYLE = f'font-family: Courier New; font-size: 12px; font-weight: 900; color: {fluorescent_pink};'
CREATE_NEW_PROJECT_WINDOW_ICON = ''
CREATE_NEW_PROJECT_WINDOW_H = 160
CREATE_NEW_PROJECT_WINDOW_W = 500
CREATE_NEW_PROJECT_DELAY_SEC = 2

# <LeftPanelHorizontalLine1> class constants
LEFT_PANEL_HORIZONTAL_LINE_STYLE = f'background-color: {black};'

# <LeftPanelFileDir1> class constants
LEFT_PANEL_FILE_DIR_STYLE = f'background-color: {blue_green}; font-family: Courier New; font-size: 12px; font-weight: 900;'

# <RightPanelFileDir1> class constants
RIGHT_PANEL_FILE_DIR_STYLE = f'background-color: #f7dc6f; font-family: Courier New; font-size: 12px; font-weight: 900;'

# <VerticalLine1> class constants
VERTICAL_LINE_STYLE = f'background-color: {black};'

# <RightPanel> class constants
RIGHT_PANEL_TTL = ''
RIGHT_PANEL_STYLE = f'font-weight: 900; color: {white};'
RIGHT_PANEL_STATUS_STYLE = f'background-color: {black}; font-size: 20px; font-weight: 900; color: {black};'
RIGHT_PANEL_WINDOW_ICON = ''
RIGHT_PANEL_WINDOW_H = 600
RIGHT_PANEL_WINDOW_W = 800

# <RightPanelLine1> class constants
RIGHT_PANEL_LINE_1_USER_IMAGE = ''  # <--- convert -resize 100x100 file_1.jpg file_2.jpg  'sid3.jpg'
RIGHT_PANEL_LINE_1_PROJECT_NAME_STYLE = f'font-size: 26px; font-weight: 900; color: {white}; background-color: {blue_green};'
RIGHT_PANEL_LINE_1_USER_NAME_STYLE = f'font-size: 18px; font-weight: 900; color: {white}; background-color: {blue_green};'
NUMBER_OF_USERS_ICON = 'fa.users'
ADD_USERS_ICON = 'fa.user-plus'
RIGHT_PANEL_LINE_1_SETTINGS_STYLE = f'background-color: {transparent}; border: 0px'

# <LocalProjectFolder> class constants
LEFT_PROJECT_OPEN_UPLOAD_COMMENT_STYLE = f'background-color: {white}; font-family: Courier New; font-size: 12px; font-weight: 700;'


