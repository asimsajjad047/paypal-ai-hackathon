INSERT INTO Part (PartID, Name, Brand, Category) VALUES
 (1,  'Ryzen 5 7600',            'AMD',          'CPU'),
 (2,  'Core i5-12400F',          'Intel',        'CPU'),
 (3,  'B650 Tomahawk WiFi',      'MSI',          'Motherboard'),
 (4,  'PRO B760M-A DDR4',        'MSI',          'Motherboard'),
 (5,  'Vengeance DDR5 32GB',     'Corsair',      'RAM'),
 (6,  'Vengeance LPX DDR4 16GB', 'Corsair',      'RAM'),
 (7,  'RTX 4070',                'NVIDIA',       'GPU'),
 (8,  'RM750e',                  'Corsair',      'PSU'),
 (9,  'H5 Flow',                 'NZXT',         'Case'),
 (10, 'Peerless Assassin 120 SE','Thermalright', 'Cooler'),
 (11, '990 Pro 1TB',             'Samsung',      'Storage');
 INSERT INTO CPU (PartID, Socket, TDP_W, HasIntegratedGraphics, Cores, BoostClock, BenchmarkScore) VALUES
 (1, 'AM5',     65, 1, 6, 5.1, 27000),
 (2, 'LGA1700', 65, 0, 6, 4.4, 19500);