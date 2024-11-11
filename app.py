# app.py

import os
import pandas as pd
import dash
from dash import html, dcc, dash_table
import plotly.express as px
import plotly.graph_objects as go
from dash.dependencies import Input, Output, State
import dash_bootstrap_components as dbc
import numpy as np
import base64
import io

# Sử dụng chủ đề Bootstrap hiện đại
external_stylesheets = [
    dbc.themes.FLATLY,
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css'
]

# Khởi tạo ứng dụng Dash với các stylesheet bên ngoài và suppress_callback_exceptions=True
app = dash.Dash(__name__, external_stylesheets=external_stylesheets, suppress_callback_exceptions=True)
app.title = 'Project Management Dashboard'
server = app.server

# Navbar
navbar = dbc.Navbar(
    dbc.Container([
        html.A(
            dbc.Row([
                dbc.Col(html.Img(src="/assets/logo.png", height="30px")),  # Thay đổi đường dẫn logo nếu cần
                dbc.Col(dbc.NavbarBrand("Project Dashboard", className="ml-2 text-white")),
            ], align="center"),
            href="#",
            style={"textDecoration": "none"}
        ),
    ], fluid=True),
    color="primary",
    dark=True,
    sticky="top",
    className="mb-4",
)

# Tạo bố cục bảng điều khiển (đặt sẵn trong layout)
dashboard_layout = html.Div([
    # Bộ lọc
    dbc.Row([
        dbc.Col([
            html.Label('Chọn Dự án:', className='font-weight-bold'),
            dcc.Dropdown(
                id='project-selector',
                options=[],  # Sẽ được cập nhật sau
                value=None,
                style={'width': '100%'}
            ),
        ], width=4),
        dbc.Col([
            html.Label('Lọc theo mức độ rủi ro:', className='font-weight-bold'),
            dcc.Dropdown(
                id='risk-filter',
                options=[
                    {'label': 'Tất cả', 'value': 'all'},
                    {'label': 'Có rủi ro', 'value': 'at_risk'},
                    {'label': 'Không có rủi ro', 'value': 'not_at_risk'},
                ],
                value='all',
                clearable=False,
            ),
        ], width=4),
        dbc.Col([
            html.Label('Tìm kiếm Dự án:', className='font-weight-bold'),
            dcc.Input(id='project-search', type='text', placeholder='Nhập tên dự án...', debounce=True, style={'width': '100%'}),
        ], width=4),
    ], className='mb-4'),
    # Lưu trữ dữ liệu đã xử lý
    dcc.Store(id='projects-extended-data'),
    dcc.Store(id='resources-processed-data'),
    dcc.Store(id='risks-processed-data'),
    # Tabs
    dbc.Tabs([
        dbc.Tab(label='Tổng quan', tab_id='tab-overview', children=[
            # Thẻ KPI
            dbc.Row([
                dbc.Col(
                    dbc.Card([
                        dbc.CardBody([
                            html.Div([
                                html.I(className="fas fa-project-diagram fa-2x text-primary"),
                                html.H5("Tổng số Dự án", className="card-title mt-2"),
                                html.H2(id='total-projects', className="card-text"),
                            ], className="text-center"),
                        ]),
                    ], className="shadow-sm h-100"),
                    width=3,
                ),
                dbc.Col(
                    dbc.Card([
                        dbc.CardBody([
                            html.Div([
                                html.I(className="fas fa-tasks fa-2x text-success"),
                                html.H5("Dự án Đang hoạt động", className="card-title mt-2"),
                                html.H2(id='active-projects', className="card-text"),
                            ], className="text-center"),
                        ]),
                    ], className="shadow-sm h-100"),
                    width=3,
                ),
                dbc.Col(
                    dbc.Card([
                        dbc.CardBody([
                            html.Div([
                                html.I(className="fas fa-check-circle fa-2x text-info"),
                                html.H5("Dự án Hoàn thành", className="card-title mt-2"),
                                html.H2(id='completed-projects', className="card-text"),
                            ], className="text-center"),
                        ]),
                    ], className="shadow-sm h-100"),
                    width=3,
                ),
                dbc.Col(
                    dbc.Card([
                        dbc.CardBody([
                            html.Div([
                                html.I(className="fas fa-exclamation-triangle fa-2x text-danger"),
                                html.H5("Dự án Có rủi ro", className="card-title mt-2"),
                                html.H2(id='at-risk-projects', className="card-text"),
                            ], className="text-center"),
                        ]),
                    ], className="shadow-sm h-100"),
                    width=3,
                ),
            ], className="mb-4"),
            # Biểu đồ Donut cho Phân bố Trạng thái Dự án
            dbc.Row([
                dbc.Col(
                    dbc.Card([
                        dbc.CardBody([
                            html.H4("Phân bố Trạng thái Dự án", className='card-title'),
                            dcc.Graph(id='status-distribution-chart'),
                        ])
                    ], className="shadow-sm"),
                    width=6,
                ),
                dbc.Col(
                    dbc.Card([
                        dbc.CardBody([
                            html.H4("Biến động Ngân sách", className='card-title'),
                            dcc.Graph(id='budget-variance-chart'),
                        ])
                    ], className="shadow-sm"),
                    width=6,
                ),
            ], className='mb-4'),
            # Tiến độ Dự án Tổng thể với Thanh Tiến trình
            dbc.Row([
                dbc.Col(
                    dbc.Card([
                        dbc.CardBody([
                            html.H4([
                                html.I(className='fas fa-chart-line mr-2'),
                                'Tiến độ Dự án Tổng thể'
                            ], className='card-title'),
                            html.Div(id='project-progress-bars'),
                        ])
                    ], className="shadow-sm"),
                    width=12
                ),
            ], className='mb-4'),
        ]),
        dbc.Tab(label='Chi tiết', tab_id='tab-details', children=[
            # Chi tiết Dự án và Dòng thời gian
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody(id='project-details'),
                    ], className="shadow-sm"),
                ], width=4),
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader(html.H4([
                            html.I(className='fas fa-project-diagram mr-2'),
                            'Dòng thời gian Dự án'
                        ])),
                        dbc.CardBody([
                            dcc.Graph(id='gantt-chart'),
                        ]),
                    ], className="shadow-sm"),
                ], width=8),
            ], className='mb-4'),
            # Các Biểu đồ Bổ sung
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader(html.H4([
                            html.I(className='fas fa-dollar-sign mr-2'),
                            'Chi phí theo Thời gian'
                        ])),
                        dbc.CardBody([
                            dcc.Graph(id='cost-over-time-chart'),
                        ]),
                    ], className="shadow-sm"),
                ], width=12),
            ], className='mb-4'),
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader(html.H4([
                            html.I(className='fas fa-chart-area mr-2'),
                            'Biểu đồ Burn-down'
                        ])),
                        dbc.CardBody([
                            dcc.Graph(id='burndown-chart'),
                        ]),
                    ], className="shadow-sm"),
                ], width=12),
            ], className='mb-4'),
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader(html.H4([
                            html.I(className='fas fa-exclamation-triangle mr-2'),
                            'Phân tích Rủi ro'
                        ])),
                        dbc.CardBody([
                            dcc.Graph(id='risk-matrix'),
                            html.H5('Chi tiết Rủi ro', className='mt-4'),
                            html.Div(id='risk-table'),
                        ]),
                    ], className="shadow-sm"),
                ], width=12),
            ], className='mb-4'),
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader(html.H4([
                            html.I(className='fas fa-users mr-2'),
                            'Phân bổ Tài nguyên'
                        ])),
                        dbc.CardBody([
                            dcc.Graph(id='resource-utilization-chart'),
                        ]),
                    ], className="shadow-sm"),
                ], width=12),
            ], className='mb-4'),
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader(html.H4([
                            html.I(className='fas fa-bell mr-2'),
                            'Cảnh báo & Vấn đề'
                        ])),
                        dbc.CardBody(id='alerts-issues'),
                    ], className="shadow-sm"),
                ], width=12),
            ], className='mb-4'),
        ]),
    ], id='tabs', active_tab='tab-overview'),
])

# Layout
app.layout = dbc.Container([
    navbar,
    # Upload components và nút Load Dashboard
    html.Div([
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.Label('Tải lên tệp Dự án:', className='font-weight-bold'),
                    dcc.Upload(
                        id='upload-projects',
                        children=dbc.Button('Chọn tệp Dự án', color='secondary', className='mt-2'),
                        multiple=False
                    ),
                ], className='upload-box'),
            ], width=3),
            dbc.Col([
                html.Div([
                    html.Label('Tải lên tệp Mốc:', className='font-weight-bold'),
                    dcc.Upload(
                        id='upload-milestones',
                        children=dbc.Button('Chọn tệp Mốc', color='secondary', className='mt-2'),
                        multiple=False
                    ),
                ], className='upload-box'),
            ], width=3),
            dbc.Col([
                html.Div([
                    html.Label('Tải lên tệp Tài nguyên:', className='font-weight-bold'),
                    dcc.Upload(
                        id='upload-resources',
                        children=dbc.Button('Chọn tệp Tài nguyên', color='secondary', className='mt-2'),
                        multiple=False
                    ),
                ], className='upload-box'),
            ], width=3),
            dbc.Col([
                html.Div([
                    html.Label('Tải lên tệp Rủi ro:', className='font-weight-bold'),
                    dcc.Upload(
                        id='upload-risks',
                        children=dbc.Button('Chọn tệp Rủi ro', color='secondary', className='mt-2'),
                        multiple=False
                    ),
                ], className='upload-box'),
            ], width=3),
        ], className='mb-3'),
        dbc.Row([
            dbc.Col([
                dbc.Button('Tải Bảng điều khiển', id='load-dashboard-button', color='success', className='mr-2', n_clicks=0)
            ], width=12, className='text-center')
        ]),
    ], className='upload-section'),
    # Thông báo tải lên thành công
    dbc.Alert(id='upload-alert', is_open=False, duration=4000),
    # Store components
    dcc.Store(id='projects-data'),
    dcc.Store(id='milestones-data'),
    dcc.Store(id='resources-data'),
    dcc.Store(id='risks-data'),
    # Nội dung Bảng điều khiển (ẩn ban đầu)
    html.Div(id='dashboard-content', style={'display': 'none'}),
    # Dummy output cho clientside callback
    html.Div(id='dummy-output', style={'display': 'none'})
], fluid=True)

# Thêm CSS tùy chỉnh
app.clientside_callback(
    """
    function(_) {
        const style = document.createElement('style');
        style.innerHTML = `
            body { font-family: 'Roboto', sans-serif; }
            .upload-box { background: #f9f9f9; padding: 15px; border-radius: 5px; text-align: center; }
            .upload-section { background: #f0f4f7; padding: 20px; border-radius: 5px; margin-bottom: 20px; }
            .card-title { font-weight: bold; }
            .nav-link { font-weight: bold; }
        `;
        document.head.appendChild(style);
        return null;
    }
    """,
    Output('dummy-output', 'children'),
    Input('load-dashboard-button', 'n_clicks'),
    prevent_initial_call=True
)

# Hàm phân tích nội dung tệp tải lên
def parse_contents(contents, filename):
    if contents is None:
        return None
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    try:
        if 'xls' in filename:
            # Giả sử rằng người dùng đã tải lên một tệp Excel
            df = pd.read_excel(io.BytesIO(decoded))
        else:
            # Giả sử rằng người dùng đã tải lên một tệp CSV
            df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
    except Exception as e:
        print(e)
        return None
    return df

# Callback để tải dữ liệu từ các tệp tải lên
@app.callback(
    [Output('projects-data', 'data'),
     Output('milestones-data', 'data'),
     Output('resources-data', 'data'),
     Output('risks-data', 'data'),
     Output('upload-alert', 'children'),
     Output('upload-alert', 'color'),
     Output('upload-alert', 'is_open'),
     Output('dashboard-content', 'children'),
     Output('dashboard-content', 'style')],
    [Input('load-dashboard-button', 'n_clicks')],
    [State('upload-projects', 'contents'),
     State('upload-projects', 'filename'),
     State('upload-milestones', 'contents'),
     State('upload-milestones', 'filename'),
     State('upload-resources', 'contents'),
     State('upload-resources', 'filename'),
     State('upload-risks', 'contents'),
     State('upload-risks', 'filename')]
)
def load_data(n_clicks, projects_contents, projects_filename,
              milestones_contents, milestones_filename,
              resources_contents, resources_filename,
              risks_contents, risks_filename):
    if n_clicks > 0:
        # Kiểm tra xem tất cả các tệp đã được tải lên chưa
        if not all([projects_contents, milestones_contents, resources_contents, risks_contents]):
            return [None, None, None, None, 'Vui lòng tải lên tất cả các tệp cần thiết', 'danger', True, dash.no_update, {'display': 'none'}]
        # Phân tích các tệp tải lên
        df_projects = parse_contents(projects_contents, projects_filename)
        df_milestones = parse_contents(milestones_contents, milestones_filename)
        df_resources = parse_contents(resources_contents, resources_filename)
        df_risks = parse_contents(risks_contents, risks_filename)
        if df_projects is None or df_milestones is None or df_resources is None or df_risks is None:
            return [None, None, None, None, 'Lỗi khi tải dữ liệu', 'danger', True, dash.no_update, {'display': 'none'}]
        else:
            # Chuyển đổi DataFrame thành JSON để lưu trữ trong dcc.Store
            projects_data = df_projects.to_json(date_format='iso', orient='split')
            milestones_data = df_milestones.to_json(date_format='iso', orient='split')
            resources_data = df_resources.to_json(date_format='iso', orient='split')
            risks_data = df_risks.to_json(date_format='iso', orient='split')
            return [projects_data, milestones_data, resources_data, risks_data, 'Tải dữ liệu thành công!', 'success', True, dashboard_layout, {'display': 'block'}]
    else:
        return [dash.no_update]*9

# Callback để xử lý và lưu trữ dữ liệu đã xử lý
@app.callback(
    [Output('projects-extended-data', 'data'),
     Output('resources-processed-data', 'data'),
     Output('risks-processed-data', 'data'),
     Output('total-projects', 'children'),
     Output('active-projects', 'children'),
     Output('completed-projects', 'children'),
     Output('at-risk-projects', 'children')],
    [Input('projects-data', 'data'),
     Input('milestones-data', 'data'),
     Input('resources-data', 'data'),
     Input('risks-data', 'data')]
)
def process_data(projects_data, milestones_data, resources_data, risks_data):
    if projects_data and milestones_data and resources_data and risks_data:
        # Giải mã dữ liệu
        df_projects = pd.read_json(projects_data, orient='split')
        df_milestones = pd.read_json(milestones_data, orient='split')
        df_resources = pd.read_json(resources_data, orient='split')
        df_risks = pd.read_json(risks_data, orient='split')

        # Xử lý dữ liệu và tính toán
        # Chuyển đổi các cột ngày tháng về định dạng datetime
        date_columns = {
            'df_projects': ['StartDate', 'EndDate', 'ExpectedEndDate'],
            'df_milestones': ['MilestoneStartDate', 'MilestoneEndDate', 'ActualCompletionDate'],
            'df_risks': ['DateIdentified', 'RiskReviewDate']
        }

        dfs = {'df_projects': df_projects, 'df_milestones': df_milestones, 'df_risks': df_risks}

        for df_name, columns in date_columns.items():
            df = dfs[df_name]
            for col in columns:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], errors='coerce')

        # Hàm tính toán tiến độ dự án
        def calculate_project_completion():
            project_completion = []
            for project_id in df_projects['ProjectID']:
                milestones = df_milestones[df_milestones['ProjectID'] == project_id]
                if not milestones.empty and 'PercentComplete' in milestones.columns:
                    percent_complete = milestones['PercentComplete'].mean()
                else:
                    percent_complete = 0
                project_completion.append({'ProjectID': project_id, 'PercentComplete': percent_complete})
            df_completion = pd.DataFrame(project_completion)
            df_projects_extended = pd.merge(df_projects, df_completion, on='ProjectID')
            return df_projects_extended

        df_projects_extended = calculate_project_completion()

        # Tính toán biến động ngân sách
        df_projects_extended['BudgetVariance'] = df_projects_extended['Budget'] - df_projects_extended['ActualCost']

        # Ánh xạ mức độ tác động và xác suất thành giá trị số
        impact_mapping = {'Low': 1, 'Medium': 2, 'High': 3}
        probability_mapping = {'Low': 1, 'Medium': 2, 'High': 3}

        df_risks['ImpactLevelNum'] = df_risks['ImpactLevel'].map(impact_mapping)
        df_risks['ProbabilityNum'] = df_risks['Probability'].map(probability_mapping)
        df_risks['RiskScore'] = df_risks['ImpactLevelNum'] * df_risks['ProbabilityNum']

        # Xác định các rủi ro cao
        high_risk_threshold = 6  # Bạn có thể điều chỉnh giá trị này
        df_high_risks = df_risks[
            (df_risks['RiskScore'] >= high_risk_threshold) &
            (df_risks['RiskStatus'].str.strip().str.lower() == 'open')
        ]

        # Lấy danh sách các ProjectID có rủi ro cao
        at_risk_project_ids = df_high_risks['ProjectID'].unique()

        # Số lượng dự án "At Risk"
        at_risk_projects_count = len(at_risk_project_ids)

        # Tính số lượng dự án "Active"
        active_projects = df_projects[
            df_projects['ProjectStatus'].str.strip().str.lower().isin(['in progress', 'not started'])
        ]
        active_projects = active_projects[~active_projects['ProjectID'].isin(at_risk_project_ids)]
        active_projects_count = active_projects.shape[0]

        # Số lượng dự án hoàn thành
        completed_projects_count = df_projects[df_projects['ProjectStatus'].str.strip().str.lower() == 'completed'].shape[0]

        # Thêm cột 'IsAtRisk' vào df_projects_extended
        df_projects_extended['IsAtRisk'] = df_projects_extended['ProjectID'].isin(at_risk_project_ids)

        # Tính toán cột 'StatusIndicator'
        df_projects_extended['StatusIndicator'] = df_projects_extended['IsAtRisk'].apply(lambda x: '⚠️' if x else '✅')

        # Tính toán SPI và CPI
        def calculate_spi_cpi():
            spi_cpi_list = []
            for project_id in df_projects_extended['ProjectID']:
                project = df_projects_extended[df_projects_extended['ProjectID'] == project_id]

                # Extract scalar values
                percent_complete = project['PercentComplete'].values[0] / 100
                expected_end_date = project['ExpectedEndDate'].values[0]
                start_date = project['StartDate'].values[0]
                end_date = project['EndDate'].values[0]
                actual_cost = project['ActualCost'].values[0]
                budget = project['Budget'].values[0]

                # Calculate durations
                total_duration = (expected_end_date - start_date) / np.timedelta64(1, 'D') if pd.notnull(expected_end_date) and pd.notnull(start_date) else np.nan
                planned_duration = (end_date - start_date) / np.timedelta64(1, 'D') if pd.notnull(end_date) and pd.notnull(start_date) else np.nan

                # Calculate schedule variance in days
                schedule_variance = percent_complete * total_duration if total_duration is not np.nan else np.nan

                # Calculate SPI (Schedule Performance Index)
                if planned_duration and planned_duration > 0:
                    spi = schedule_variance / planned_duration
                else:
                    spi = np.nan

                # Calculate CPI (Cost Performance Index)
                if actual_cost > 0:
                    cpi = budget / actual_cost
                else:
                    cpi = np.nan

                spi_cpi_list.append({'ProjectID': project_id, 'SPI': spi, 'CPI': cpi})

            df_spi_cpi = pd.DataFrame(spi_cpi_list)
            df_projects_extended2 = pd.merge(df_projects_extended, df_spi_cpi, on='ProjectID')
            return df_projects_extended2

        # Cập nhật DataFrame mở rộng với SPI và CPI
        df_projects_extended = calculate_spi_cpi()

        # Xử lý dữ liệu sử dụng tài nguyên
        if 'AllocatedHours' in df_resources.columns and 'TotalCapacity' in df_resources.columns:
            df_resources['Utilization'] = (df_resources['AllocatedHours'] / df_resources['TotalCapacity']) * 100
            df_resources['Utilization'] = df_resources['Utilization'].round(2)
        else:
            df_resources['Utilization'] = 0

        # Tạo danh sách các mức ưu tiên với màu sắc tương ứng
        priority_color_map = {'High': 'danger', 'Medium': 'warning', 'Low': 'success'}
        df_projects_extended['PriorityColor'] = df_projects_extended['Priority'].map(priority_color_map)

        # Chuyển đổi DataFrame thành JSON để lưu trữ trong dcc.Store
        projects_extended_data = df_projects_extended.to_json(date_format='iso', orient='split')
        resources_processed_data = df_resources.to_json(date_format='iso', orient='split')
        risks_processed_data = df_risks.to_json(date_format='iso', orient='split')

        return [projects_extended_data, resources_processed_data, risks_processed_data,
                f"{len(df_projects)}", f"{active_projects_count}", f"{completed_projects_count}", f"{at_risk_projects_count}"]
    else:
        return [None, None, None, "0", "0", "0", "0"]

# Cập nhật tùy chọn trong bộ chọn dự án
@app.callback(
    [Output('project-selector', 'options'),
     Output('project-selector', 'value')],
    [Input('projects-extended-data', 'data')]
)
def update_project_selector(projects_extended_data):
    if projects_extended_data is None:
        return [[], None]
    else:
        df_projects_extended = pd.read_json(projects_extended_data, orient='split')
        options = [{'label': row['ProjectName'], 'value': row['ProjectID']} for _, row in df_projects_extended.iterrows()]
        value = df_projects_extended['ProjectID'].iloc[0] if not df_projects_extended.empty else None
        return [options, value]

# Cập nhật chi tiết dự án
@app.callback(
    Output('project-details', 'children'),
    [Input('project-selector', 'value'),
     Input('projects-extended-data', 'data')]
)
def update_project_details(selected_project_id, projects_extended_data):
    if not selected_project_id or not projects_extended_data:
        return html.Div("Vui lòng chọn một dự án để xem chi tiết.")

    date_columns = ['StartDate', 'EndDate', 'ExpectedEndDate']
    df_projects_extended = pd.read_json(projects_extended_data, orient='split', convert_dates=date_columns)

    # Rest of your code remains the same

    # Kiểm tra xem dự án có tồn tại trong dữ liệu hay không
    if selected_project_id not in df_projects_extended['ProjectID'].values:
        return html.Div("Dự án không tồn tại trong dữ liệu.")

    project = df_projects_extended[df_projects_extended['ProjectID'] == selected_project_id].iloc[0]

    # Xử lý các giá trị NaN hoặc None
    def format_value(value):
        return value if pd.notnull(value) else 'Không có'

    # Tính toán phần trăm ngân sách đã sử dụng
    if pd.notnull(project['Budget']) and project['Budget'] != 0:
        budget_used_percent = (project['ActualCost'] / project['Budget']) * 100
    else:
        budget_used_percent = 0

    details = [
        dbc.Accordion([
            dbc.AccordionItem([
                html.P([html.I(className='fas fa-project-diagram mr-2'), html.Strong('Dự án: '), format_value(project['ProjectName'])]),
                html.P([html.I(className='fas fa-user mr-2'), html.Strong('Quản lý Dự án: '), format_value(project['ProjectManager'])]),
                html.P([html.I(className='fas fa-info-circle mr-2'), html.Strong('Trạng thái: '), format_value(project['ProjectStatus'])]),
                html.P([html.I(className='fas fa-calendar-alt mr-2'), html.Strong('Ngày Bắt đầu: '), project['StartDate'].strftime('%Y-%m-%d') if pd.notnull(project['StartDate']) else 'Không có']),
                html.P([html.I(className='fas fa-calendar-alt mr-2'), html.Strong('Ngày Kết thúc: '), project['EndDate'].strftime('%Y-%m-%d') if pd.notnull(project['EndDate']) else 'Không có']),
                html.P([html.I(className='fas fa-calendar-alt mr-2'), html.Strong('Ngày Kết thúc Dự kiến: '), project['ExpectedEndDate'].strftime('%Y-%m-%d') if pd.notnull(project['ExpectedEndDate']) else 'Không có']),
            ], title="Thông tin Chung", item_id="info"),
            dbc.AccordionItem([
                html.P([html.I(className='fas fa-dollar-sign mr-2'), html.Strong('Ngân sách: '), f"{project['Budget']:,} VND" if pd.notnull(project['Budget']) else 'Không có']),
                html.P([html.I(className='fas fa-dollar-sign mr-2'), html.Strong('Chi phí Thực tế: '), f"{project['ActualCost']:,} VND" if pd.notnull(project['ActualCost']) else 'Không có']),
                html.P([html.I(className='fas fa-chart-line mr-2'), html.Strong('Biến động Ngân sách: '), f"{project['BudgetVariance']:,} VND" if pd.notnull(project['BudgetVariance']) else 'Không có']),
                html.P([html.I(className='fas fa-percentage mr-2'), html.Strong('Ngân sách Đã sử dụng: '), f"{budget_used_percent:.1f}%" if pd.notnull(budget_used_percent) else 'Không có']),
                # Hiển thị biến động ngân sách bằng thanh tiến trình
                dbc.Progress(
                    value=budget_used_percent,
                    label=f"Đã sử dụng: {budget_used_percent:.1f}%",
                    color='danger' if budget_used_percent > 100 else 'success',
                    striped=True,
                    animated=True,
                    className='mb-3'
                ),
            ], title="Chi tiết Tài chính", item_id="finance"),
            dbc.AccordionItem([
                html.P([html.I(className='fas fa-briefcase mr-2'), html.Strong('Ưu tiên: '), format_value(project['Priority'])]),
                html.P([html.I(className='fas fa-user-tie mr-2'), html.Strong('Khách hàng: '), format_value(project['Client'])]),
                html.P([html.I(className='fas fa-users mr-2'), html.Strong('Các Bên liên quan: '), format_value(project['Stakeholders'])]),
                html.P([html.I(className='fas fa-tasks mr-2'), html.Strong('Các Kết quả Chính: '), format_value(project['KeyDeliverables'])]),
            ], title="Thông tin Các bên liên quan", item_id="stakeholders"),
            dbc.AccordionItem([
                html.P([html.I(className='fas fa-info-circle mr-2'), html.Strong('Mô tả: '), format_value(project['Description'])]),
                html.P([html.I(className='fas fa-tasks mr-2'), html.Strong('Giai đoạn Dự án: '), format_value(project['ProjectPhase'])]),
                html.P([html.I(className='fas fa-percentage mr-2'), html.Strong('ROI: '), format_value(project['ROI'])]),
            ], title="Thông tin Bổ sung", item_id="additional"),
            dbc.AccordionItem([
                html.P([html.I(className='fas fa-percent mr-2'), html.Strong('Phần trăm Hoàn thành: '), f"{project['PercentComplete']:.2f}%" if pd.notnull(project['PercentComplete']) else 'Không có']),
                dbc.Progress(value=project['PercentComplete'] if pd.notnull(project['PercentComplete']) else 0, color="success", className="mb-3", striped=True, animated=True),
                html.P([html.I(className='fas fa-exclamation-triangle mr-2'), html.Strong('Có rủi ro: '), 'Có' if project['IsAtRisk'] else 'Không']),
            ], title="Tiến độ", item_id="progress"),
        ], start_collapsed=True, active_item="info")
    ]
    return details

# Các callback khác cập nhật biểu đồ, bảng, và các thành phần khác
# (Các hàm này giữ nguyên như trong mã của bạn)
# Cập nhật biểu đồ Gantt
@app.callback(
    Output('gantt-chart', 'figure'),
    [Input('project-selector', 'value'),
     Input('milestones-data', 'data')]
)
def update_gantt_chart(selected_project_id, milestones_data):
    if not milestones_data or not selected_project_id:
        return go.Figure()  # Return an empty figure

    # Convert JSON data to DataFrame
    df_milestones = pd.read_json(milestones_data, orient='split')
    selected_milestones = df_milestones[df_milestones['ProjectID'] == selected_project_id].copy()

    if selected_milestones.empty:
        return go.Figure()

    # Convert relevant columns to datetime
    date_columns = ['MilestoneStartDate', 'MilestoneEndDate', 'ActualCompletionDate']
    for col in date_columns:
        if col in selected_milestones.columns:
            selected_milestones[col] = pd.to_datetime(selected_milestones[col], errors='coerce')

    # Drop rows with missing start or end dates
    selected_milestones.dropna(subset=['MilestoneStartDate', 'MilestoneEndDate'], inplace=True)

    if selected_milestones.empty:
        return go.Figure()

    # Define color mapping based on Status
    colors = {
        'Not Started': 'lightgray',
        'In Progress': '#17a2b8',
        'Completed': '#28a745',
        'Delayed': '#dc3545',
    }

    # Create the timeline using Plotly Express with 'plotly' template
    fig = px.timeline(
        selected_milestones,
        x_start='MilestoneStartDate',
        x_end='MilestoneEndDate',
        y='MilestoneName',
        color='Status',
        color_discrete_map=colors,
        hover_data={
            'Description': True,
            'PercentComplete': True,
            'MilestoneOwner': True,
            # Exclude 'MilestoneStartDate' and 'MilestoneEndDate' from hover_data
        },
        labels={
            'MilestoneName': 'Milestone',
            'Status': 'Status',
            'MilestoneStartDate': 'Start Date',
            'MilestoneEndDate': 'End Date'
        },
        template='plotly'  # Changed from 'plotly_white' to 'plotly'
    )

    # Customize hovertemplate for better control over hover information
    fig.update_traces(
        hovertemplate=(
            "Milestone: %{y}<br>"
            "Status: %{color}<br>"  # Use %{color} to display the Status text
            "Description: %{customdata[0]}<br>"
            "Percent Complete: %{customdata[1]}%<br>"
            "Milestone Owner: %{customdata[2]}<br>"
            "Start Date: %{x|%Y-%m-%d}<br>"
            "End Date: %{x_end|%Y-%m-%d}<br>"
            "<extra></extra>"
        )
    )

    # Update layout for better aesthetics
    fig.update_yaxes(autorange="reversed")  # Ensures the first milestone is at the top
    fig.update_layout(
        showlegend=True,
        margin=dict(l=40, r=40, t=40, b=40),
        hoverlabel=dict(bgcolor="white", font_size=12),
        xaxis_title='Thời gian',  # 'Time' in Vietnamese
        yaxis_title='Milestone',
        bargap=0.1  # Adjust gap between bars if necessary
    )

    return fig
# Cập nhật biểu đồ chi phí theo thời gian
@app.callback(
    Output('cost-over-time-chart', 'figure'),
    [Input('project-selector', 'value'),
     Input('projects-data', 'data')]
)
def update_cost_over_time_chart(selected_project_id, projects_data):
    # Nội dung hàm như trong code trước

    if projects_data is None or selected_project_id is None:
        return go.Figure()
    df_projects = pd.read_json(projects_data, orient='split')
    project = df_projects[df_projects['ProjectID'] == selected_project_id].iloc[0]

    start_date = project['StartDate']
    end_date = project['ExpectedEndDate']
    if pd.isnull(start_date) or pd.isnull(end_date):
        return go.Figure()
    dates = pd.date_range(start=start_date, end=end_date, freq='W')
    planned_cost = np.linspace(0, project['Budget'], len(dates))
    actual_cost = np.cumsum(np.random.uniform(0, project['Budget']/len(dates), len(dates)))

    df_cost = pd.DataFrame({
        'Date': dates,
        'Planned Cost': planned_cost,
        'Actual Cost': actual_cost
    })

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_cost['Date'], y=df_cost['Planned Cost'], mode='lines', name='Chi phí Kế hoạch'))
    fig.add_trace(go.Scatter(x=df_cost['Date'], y=df_cost['Actual Cost'], mode='lines', name='Chi phí Thực tế'))

    fig.update_layout(
        template='plotly_white',
        margin=dict(l=20, r=20, t=50, b=20),
        legend_title_text='Loại Chi phí',
        hoverlabel=dict(bgcolor="white", font_size=12),
        xaxis_title='Ngày',
        yaxis_title='Chi phí',
    )

    return fig

# Cập nhật biểu đồ Burn-down
@app.callback(
    Output('burndown-chart', 'figure'),
    [Input('project-selector', 'value'),
     Input('milestones-data', 'data')]
)
def update_burndown_chart(selected_project_id, milestones_data):
    # Nội dung hàm như trong code trước

    if milestones_data is None or selected_project_id is None:
        return go.Figure()
    df_milestones = pd.read_json(milestones_data, orient='split')
    selected_milestones = df_milestones[df_milestones['ProjectID'] == selected_project_id]
    if selected_milestones.empty:
        return go.Figure()
    total_tasks = len(selected_milestones)
    start_date = selected_milestones['MilestoneStartDate'].min()
    end_date = selected_milestones['MilestoneEndDate'].max()
    if pd.isnull(start_date) or pd.isnull(end_date):
        return go.Figure()
    dates = pd.date_range(start=start_date, end=end_date, freq='W')
    remaining_tasks = total_tasks - np.cumsum(np.random.randint(0, 2, len(dates)))
    remaining_tasks = np.maximum(remaining_tasks, 0)  # Đảm bảo không có giá trị âm

    df_burndown = pd.DataFrame({
        'Date': dates,
        'Remaining Tasks': remaining_tasks
    })

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_burndown['Date'], y=df_burndown['Remaining Tasks'], mode='lines+markers', name='Nhiệm vụ Còn lại'))

    fig.update_layout(
        template='plotly_white',
        margin=dict(l=20, r=20, t=50, b=20),
        legend_title_text='Nhiệm vụ',
        hoverlabel=dict(bgcolor="white", font_size=12),
        xaxis_title='Ngày',
        yaxis_title='Nhiệm vụ Còn lại',
    )

    return fig

# Cập nhật phân tích rủi ro
@app.callback(
    [Output('risk-matrix', 'figure'),
     Output('risk-table', 'children')],
    [Input('project-selector', 'value'),
     Input('risks-processed-data', 'data')]
)
def update_risk_section(selected_project_id, risks_processed_data):
    # Nội dung hàm như trong code trước

    if risks_processed_data is None or selected_project_id is None:
        return go.Figure(), html.P("Không có rủi ro liên quan đến dự án này.")
    df_risks = pd.read_json(risks_processed_data, orient='split')
    selected_risks = df_risks[df_risks['ProjectID'] == selected_project_id]

    if selected_risks.empty:
        return go.Figure(), html.P("Không có rủi ro liên quan đến dự án này.")

    fig = px.scatter(
        selected_risks,
        x='ProbabilityNum',
        y='ImpactLevelNum',
        size='RiskScore',
        color='RiskCategory',
        hover_data=['RiskDescription', 'MitigationPlan', 'RiskStatus', 'RiskOwner', 'RiskTrigger', 'ContingencyPlan', 'ResidualRisk'],
        template='plotly_white',
        color_discrete_sequence=px.colors.qualitative.Safe,
    )

    fig.update_layout(
        xaxis_title='Xác suất',
        yaxis_title='Tác động',
        xaxis=dict(
            tickmode='array',
            tickvals=[1, 2, 3],
            ticktext=['Thấp', 'Trung bình', 'Cao']
        ),
        yaxis=dict(
            tickmode='array',
            tickvals=[1, 2, 3],
            ticktext=['Thấp', 'Trung bình', 'Cao']
        ),
        margin=dict(l=20, r=20, t=20, b=20),
        legend_title_text='Loại Rủi ro',
        hoverlabel=dict(bgcolor="white", font_size=12),
    )

    risk_table = dash_table.DataTable(
        columns=[{"name": i, "id": i} for i in ['RiskID', 'RiskDescription', 'ImpactLevel', 'Probability', 'RiskScore', 'RiskStatus', 'RiskOwner', 'RiskTrigger', 'ContingencyPlan', 'ResidualRisk']],
        data=selected_risks.to_dict('records'),
        style_cell={'textAlign': 'left', 'padding': '5px'},
        style_header={
            'backgroundColor': '#f9f9f9',
            'fontWeight': 'bold',
            'border': '1px solid #e0e0e0',
        },
        style_data={
            'border': '1px solid #e0e0e0',
        },
        style_table={'overflowX': 'auto'},
    )

    return fig, risk_table

# Cập nhật biểu đồ sử dụng tài nguyên
@app.callback(
    Output('resource-utilization-chart', 'figure'),
    [Input('project-selector', 'value'),
     Input('resources-processed-data', 'data')]
)
def update_resource_utilization_chart(selected_project_id, resources_processed_data):
    if resources_processed_data is None or selected_project_id is None:
        return go.Figure()
    df_resources = pd.read_json(resources_processed_data, orient='split')
    selected_resources = df_resources[df_resources['ProjectID'] == selected_project_id]

    if selected_resources.empty:
        return go.Figure()

    # Remove or modify the 'template' parameter
    fig = px.bar(
        selected_resources,
        x='ResourceName',
        y='Utilization',
        color='Role',
        hover_data=['Skills', 'Availability', 'ActualHoursWorked', 'CostPerHour', 'ResourceType', 'OvertimeHours', 'PerformanceRating'],
        labels={'Utilization': 'Sử dụng (%)', 'ResourceName': 'Tài nguyên'},
        color_discrete_sequence=px.colors.qualitative.Vivid,
    )

    fig.update_layout(
        yaxis=dict(ticksuffix='%'),
        xaxis_tickangle=-45,
        margin=dict(l=20, r=20, t=20, b=20),
        hoverlabel=dict(bgcolor="white", font_size=12),
        legend_title_text='Vai trò',
    )

    return fig


# Cập nhật cảnh báo và vấn đề
@app.callback(
    Output('alerts-issues', 'children'),
    [Input('project-selector', 'value'),
     Input('projects-extended-data', 'data'),
     Input('risks-processed-data', 'data'),
     Input('milestones-data', 'data')]
)
def update_alerts_issues(selected_project_id, projects_extended_data, risks_processed_data, milestones_data):
    # Nội dung hàm như trong code trước

    if projects_extended_data is None or selected_project_id is None:
        return html.Div()
    df_projects_extended = pd.read_json(projects_extended_data, orient='split')
    df_risks = pd.read_json(risks_processed_data, orient='split')
    df_milestones = pd.read_json(milestones_data, orient='split')

    # Lấy dữ liệu dự án
    project = df_projects_extended[df_projects_extended['ProjectID'] == selected_project_id].iloc[0]
    alerts = []
    if pd.notnull(project['ExpectedEndDate']) and pd.notnull(project['EndDate']):
        if project['ExpectedEndDate'] > project['EndDate']:
            alerts.append(dbc.Alert("Dự án dự kiến sẽ vượt quá ngày kết thúc kế hoạch.", color='warning'))

    if project['BudgetVariance'] < 0:
        alerts.append(dbc.Alert("Dự án vượt quá ngân sách.", color='danger'))

    # Kiểm tra các vấn đề rủi ro cao
    selected_risks = df_risks[df_risks['ProjectID'] == selected_project_id]
    high_risks = selected_risks[selected_risks['RiskScore'] >= 6]
    if not high_risks.empty:
        alerts.append(dbc.Alert("Phát hiện các vấn đề rủi ro cao.", color='danger'))

    # Hiển thị các vấn đề từ mốc
    selected_milestones = df_milestones[df_milestones['ProjectID'] == selected_project_id]
    if 'Issues' in selected_milestones.columns:
        issues = selected_milestones['Issues'].dropna()
        if not issues.empty:
            alerts.append(dbc.Alert("Các vấn đề được báo cáo trong các mốc:", color='warning'))
            for issue in issues:
                alerts.append(html.P(f"- {issue}", style={'marginLeft': '20px'}))

    if not alerts:
        alerts.append(dbc.Alert("Không có cảnh báo. Dự án đang theo đúng tiến độ.", color='success'))

    return alerts

# Cập nhật biểu đồ phân bố trạng thái dự án
@app.callback(
    Output('status-distribution-chart', 'figure'),
    [Input('projects-extended-data', 'data')]
)
def update_status_distribution_chart(projects_extended_data):
    # Nội dung hàm như trong code trước

    if projects_extended_data is None:
        return go.Figure()
    df_projects_extended = pd.read_json(projects_extended_data, orient='split')
    status_counts = df_projects_extended['ProjectStatus'].value_counts()
    if len(status_counts) == 0:
        fig = go.Figure()
        fig.add_annotation(text="Không có dữ liệu trạng thái dự án",
                           xref="paper", yref="paper",
                           showarrow=False, font_size=20)
        return fig
    else:
        fig = px.pie(
            names=status_counts.index,
            values=status_counts.values,
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Pastel,
        )
        fig.update_traces(textinfo='percent+label')
        fig.update_layout(
            margin=dict(l=20, r=20, t=50, b=20),
            legend_title_text='Trạng thái Dự án',
            hoverlabel=dict(bgcolor="white", font_size=12),
        )
        return fig

# Cập nhật biểu đồ biến động ngân sách
@app.callback(
    Output('budget-variance-chart', 'figure'),
    [Input('projects-extended-data', 'data')]
)
def update_budget_variance_chart(projects_extended_data):
    # Nội dung hàm như trong code trước

    if projects_extended_data is None:
        return go.Figure()
    df_projects_extended = pd.read_json(projects_extended_data, orient='split')
    budget_variance = df_projects_extended['BudgetVariance']
    project_names = df_projects_extended['ProjectName']
    colors = ['#28a745' if val >= 0 else '#dc3545' for val in budget_variance]

    fig = go.Figure(go.Bar(
        x=project_names,
        y=budget_variance,
        marker_color=colors,
        text=[f"{val:,} VND" for val in budget_variance],
        textposition='outside',
    ))

    fig.update_layout(
        template='plotly_white',
        xaxis_tickangle=-45,
        margin=dict(l=20, r=20, t=50, b=20),
        xaxis_title='Dự án',
        yaxis_title='Biến động Ngân sách (VND)',
        hoverlabel=dict(bgcolor="white", font_size=12),
    )
    return fig

# Cập nhật thanh tiến trình dự án
@app.callback(
    Output('project-progress-bars', 'children'),
    [Input('risk-filter', 'value'),
     Input('project-search', 'value'),
     Input('projects-extended-data', 'data')]
)
def update_project_progress_bars(risk_filter, search_value, projects_extended_data):
    # Nội dung hàm như trong code trước

    if projects_extended_data is None:
        return html.Div()
    df_projects_extended = pd.read_json(projects_extended_data, orient='split')

    filtered_df = df_projects_extended.copy()
    if risk_filter == 'at_risk':
        filtered_df = filtered_df[filtered_df['IsAtRisk']]
    elif risk_filter == 'not_at_risk':
        filtered_df = filtered_df[~filtered_df['IsAtRisk']]
    if search_value:
        filtered_df = filtered_df[filtered_df['ProjectName'].str.contains(search_value, case=False)]

    project_progress_bars = []
    for _, project in filtered_df.iterrows():
        progress_bar = dbc.Progress(
            value=project['PercentComplete'],
            label=f"{project['StatusIndicator']} {project['ProjectName']} - {project['PercentComplete']:.1f}%",
            color='danger' if project['IsAtRisk'] else 'success',
            striped=True,
            animated=True,
            className='mb-2',
        )
        project_progress_bars.append(progress_bar)

    if not project_progress_bars:
        return html.P("Không có dự án nào phù hợp với tiêu chí đã chọn.")

    return project_progress_bars

if __name__ == '__main__':
    app.run_server(debug=True)
