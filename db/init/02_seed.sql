-- Sample data for development and demos

INSERT IGNORE INTO ipc_frontier (ipc_code, is_frontier, note) VALUES
('G06N', 1, '人工智能前沿'),
('H01L', 1, '半导体'),
('C08F', 0, '常规高分子');

INSERT IGNORE INTO industry_data (ipc_prefix, market_size, growth_rate, competition_level, policy_support, max_market_value) VALUES
('G06N', 1200.00, 18.50, '中', 85, 50000.00),
('H01L', 3500.00, 12.00, '高', 90, 120000.00),
('C08F', 800.00, 6.50, '低', 60, 20000.00);

INSERT IGNORE INTO ipc_citation_stats (ipc_prefix, grant_year, avg_citation, sample_size) VALUES
('G06N', 2022, 8.50, 120),
('G06N', 2023, 6.20, 150),
('H01L', 2022, 12.00, 200),
('C08F', 2022, 3.50, 80);

INSERT IGNORE INTO patents (
    patent_id, title, abstract, claims, applicant, inventor,
    application_no, ipc_code, grant_year, legal_status, citation_count, has_award
) VALUES
(
    'CN202310001234.5',
    '基于大语言模型的专利创新度评估方法及系统',
    '本发明公开了一种利用大语言模型对专利文本进行语义分析并输出创新度评分的方法，适用于知识产权金融科技场景。',
    '1.一种专利创新度评估方法，其特征在于，包括：获取专利文本；利用语言模型提取创新点；计算创新分数。',
    '某某科技有限公司',
    '张三;李四',
    '202310001234.5',
    'G06N3/00',
    2023,
    '有效',
    15,
    1
),
(
    'CN202210009876.1',
    '一种高分子复合材料及其制备方法',
    '本发明涉及一种具有优异耐热性的高分子复合材料，通过调控单体配比提升机械性能。',
    '1.一种高分子复合材料，其特征在于，包含组分A和组分B。',
    '某某材料股份有限公司',
    '王五',
    '202210009876.1',
    'C08F220/00',
    2022,
    '有效',
    4,
    0
),
(
    'CN202110005555.8',
    '半导体封装结构及制造方法',
    '本发明提供一种降低热阻的半导体封装结构，适用于功率器件封装。',
    '1.一种半导体封装结构，其特征在于，包括基板、芯片和散热层。',
    '某某半导体有限公司',
    '赵六;钱七',
    '202110005555.8',
    'H01L23/00',
    2021,
    '有效',
    22,
    0
);

INSERT IGNORE INTO patent_citations (patent_id, cited_patent_id) VALUES
('CN202310001234.5', 'CN202110005555.8');
