PRAGMA foreign_keys = ON;

-- ===== PARTS (general info) =====
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

-- ===== DETAILS FOR EACH PART TYPE =====
INSERT INTO CPU (PartID, Socket, TDP_W, HasIntegratedGraphics, Cores, BoostClock, BenchmarkScore) VALUES
 (1, 'AM5',     65, 1, 6, 5.1, 27000),
 (2, 'LGA1700', 65, 0, 6, 4.4, 19500);

INSERT INTO Motherboard (PartID, Socket, FormFactor, RAMType, RAMSlots, MaxRAM_GB, M2Slots) VALUES
 (3, 'AM5',     'ATX',       'DDR5', 4, 192, 3),
 (4, 'LGA1700', 'Micro-ATX', 'DDR4', 4, 128, 2);

INSERT INTO RAM (PartID, RAMType, Speed_MHz, ModuleCount, TotalCapacity_GB) VALUES
 (5, 'DDR5', 6000, 2, 32),
 (6, 'DDR4', 3200, 2, 16);

INSERT INTO GPU (PartID, Length_mm, TDP_W, VRAM_GB, BenchmarkScore) VALUES
 (7, 244, 200, 12, 26900);

INSERT INTO PSU (PartID, Wattage, FormFactor) VALUES
 (8, 750, 'ATX');

INSERT INTO PCCase (PartID, MaxGPULength_mm, MaxCoolerHeight_mm, PSUFormFactor) VALUES
 (9, 365, 165, 'ATX');

INSERT INTO CaseFormFactor (PartID, FormFactor) VALUES
 (9, 'ATX'),
 (9, 'Micro-ATX'),
 (9, 'Mini-ITX');

INSERT INTO Cooler (PartID, Height_mm) VALUES
 (10, 155);

INSERT INTO CoolerSocket (PartID, Socket) VALUES
 (10, 'AM4'),
 (10, 'AM5'),
 (10, 'LGA1700');

INSERT INTO Storage (PartID, Interface, Capacity_GB) VALUES
 (11, 'M.2 NVMe', 1000);

-- ===== SELLERS =====
INSERT INTO Seller (SellerID, Name, PayPalEmail, SellerType, MinPriceFactor) VALUES
 (1, 'PartsCo',      'partsco@business.example.com',   'Shop',       1.00),
 (2, 'TechDeals',    'techdeals@business.example.com', 'Shop',       1.00),
 (3, 'Dave (used)',  'dave@business.example.com',      'Individual', 0.85),
 (4, 'Priya (used)', 'priya@business.example.com',     'Individual', 0.90);

-- ===== LISTINGS (test data - real web prices come later) =====
INSERT INTO Listing (ListingID, PartID, SellerID, Condition, Price) VALUES
 (1,  1,  1, 'New', 199),
 (2,  2,  1, 'New', 129),
 (3,  3,  2, 'New', 189),
 (4,  4,  2, 'New', 119),
 (5,  5,  1, 'New',  95),
 (6,  6,  1, 'New',  39),
 (7,  7,  2, 'New', 549),
 (8,  8,  1, 'New',  89),
 (9,  9,  2, 'New',  89),
 (10, 10, 1, 'New',  35),
 (11, 11, 2, 'New',  99),
 (12, 7,  1, 'New', 539),
 (13, 7,  3, 'Used', 380),
 (14, 1,  4, 'Used', 150),
 (15, 5,  3, 'Used',  70);

 -- ===== DELIBERATELY "PROBLEM" PARTS FOR TESTING =====
INSERT INTO Part (PartID, Name, Brand, Category) VALUES
 (12, 'RTX 4090 Gaming OC', 'Gigabyte',      'GPU'),   -- very long, very power hungry
 (13, 'MWE 450 Bronze V2',  'Cooler Master', 'PSU'),   -- weak PSU
 (14, 'NR200P',             'Cooler Master', 'Case');  -- small Mini-ITX case

INSERT INTO GPU (PartID, Length_mm, TDP_W, VRAM_GB, BenchmarkScore) VALUES
 (12, 340, 450, 24, 38000);

INSERT INTO PSU (PartID, Wattage, FormFactor) VALUES
 (13, 450, 'ATX');

INSERT INTO PCCase (PartID, MaxGPULength_mm, MaxCoolerHeight_mm, PSUFormFactor) VALUES
 (14, 330, 155, 'SFX');

INSERT INTO CaseFormFactor (PartID, FormFactor) VALUES
 (14, 'Mini-ITX');

INSERT INTO Listing (ListingID, PartID, SellerID, Condition, Price) VALUES
 (16, 12, 2, 'New', 1699),
 (17, 13, 1, 'New',   45),
 (18, 14, 2, 'New',   99);
-- ===== MORE PARTS SO THE PICKER HAS REAL CHOICES =====
-- Benchmark scores are approximate PassMark-style numbers (CPU Mark / G3D Mark).
INSERT INTO Part (PartID, Name, Brand, Category) VALUES
 (15, 'Ryzen 5 5600',              'AMD',          'CPU'),
 (16, 'Ryzen 7 7800X3D',           'AMD',          'CPU'),
 (17, 'Core i5-13400F',            'Intel',        'CPU'),
 (18, 'Core i7-14700K',            'Intel',        'CPU'),
 (19, 'Ryzen 5 7500F',             'AMD',          'CPU'),
 (20, 'B550M DS3H',                'Gigabyte',     'Motherboard'),
 (21, 'B650M Pro RS',              'ASRock',       'Motherboard'),
 (22, 'B760 Gaming X AX DDR5',     'Gigabyte',     'Motherboard'),
 (24, 'Fury Beast DDR4 32GB',      'Kingston',     'RAM'),
 (25, 'Ripjaws S5 DDR5 16GB',      'G.Skill',      'RAM'),
 (26, 'Trident Z5 DDR5 64GB',      'G.Skill',      'RAM'),
 (27, 'RX 6600',                   'AMD',          'GPU'),
 (28, 'RTX 4060',                  'NVIDIA',       'GPU'),
 (29, 'RX 7600',                   'AMD',          'GPU'),
 (30, 'RTX 4060 Ti 8GB',           'NVIDIA',       'GPU'),
 (31, 'RX 7800 XT',                'AMD',          'GPU'),
 (32, 'RTX 4070 Super',            'NVIDIA',       'GPU'),
 (33, 'RTX 4080 Super',            'NVIDIA',       'GPU'),
 (34, 'RTX 3060 12GB',             'NVIDIA',       'GPU'),
 (35, 'CV550',                     'Corsair',      'PSU'),
 (36, 'RM850e',                    'Corsair',      'PSU'),
 (37, 'SF750',                     'Corsair',      'PSU'),
 (38, '4000D Airflow',             'Corsair',      'Case'),
 (39, 'Q300L',                     'Cooler Master','Case'),
 (40, 'Freezer 36',                'Arctic',       'Cooler'),
 (41, 'AK400',                     'DeepCool',     'Cooler'),
 (42, 'P3 Plus 500GB',             'Crucial',      'Storage'),
 (43, 'NV2 1TB',                   'Kingston',     'Storage'),
 (44, 'SN580 2TB',                 'WD',           'Storage');

INSERT INTO CPU (PartID, Socket, TDP_W, HasIntegratedGraphics, Cores, BoostClock, BenchmarkScore) VALUES
 (15, 'AM4',      65, 0,  6, 4.4, 21500),
 (16, 'AM5',     120, 1,  8, 5.0, 34500),
 (17, 'LGA1700',  65, 0, 10, 4.6, 25500),
 (18, 'LGA1700', 125, 1, 20, 5.6, 53000),
 (19, 'AM5',      65, 0,  6, 5.0, 26500);

INSERT INTO Motherboard (PartID, Socket, FormFactor, RAMType, RAMSlots, MaxRAM_GB, M2Slots) VALUES
 (20, 'AM4',     'Micro-ATX', 'DDR4', 4, 128, 2),
 (21, 'AM5',     'Micro-ATX', 'DDR5', 4, 192, 2),
 (22, 'LGA1700', 'ATX',       'DDR5', 4, 192, 3);

INSERT INTO RAM (PartID, RAMType, Speed_MHz, ModuleCount, TotalCapacity_GB) VALUES
 (24, 'DDR4', 3200, 2, 32),
 (25, 'DDR5', 5600, 2, 16),
 (26, 'DDR5', 6000, 2, 64);

INSERT INTO GPU (PartID, Length_mm, TDP_W, VRAM_GB, BenchmarkScore) VALUES
 (27, 190, 132,  8, 15000),
 (28, 199, 115,  8, 19800),
 (29, 204, 165,  8, 16500),
 (30, 240, 160,  8, 22500),
 (31, 267, 263, 16, 27500),
 (32, 267, 220, 12, 30500),
 (33, 304, 320, 16, 34800),
 (34, 242, 170, 12, 17000);

INSERT INTO PSU (PartID, Wattage, FormFactor) VALUES
 (35, 550, 'ATX'),
 (36, 850, 'ATX'),
 (37, 750, 'SFX');

INSERT INTO PCCase (PartID, MaxGPULength_mm, MaxCoolerHeight_mm, PSUFormFactor) VALUES
 (38, 360, 170, 'ATX'),
 (39, 360, 159, 'ATX');

INSERT INTO CaseFormFactor (PartID, FormFactor) VALUES
 (38, 'ATX'), (38, 'Micro-ATX'), (38, 'Mini-ITX'),
 (39, 'Micro-ATX'), (39, 'Mini-ITX');

INSERT INTO Cooler (PartID, Height_mm) VALUES
 (40, 159),
 (41, 155);

INSERT INTO CoolerSocket (PartID, Socket) VALUES
 (40, 'AM4'), (40, 'AM5'), (40, 'LGA1700'), (40, 'LGA1851'),
 (41, 'AM4'), (41, 'AM5'), (41, 'LGA1700');

INSERT INTO Storage (PartID, Interface, Capacity_GB) VALUES
 (42, 'M.2 NVMe',  500),
 (43, 'M.2 NVMe', 1000),
 (44, 'M.2 NVMe', 2000);

INSERT INTO Seller (SellerID, Name, PayPalEmail, SellerType, MinPriceFactor) VALUES
 (5, 'Sam (used)', 'sam@business.example.com', 'Individual', 0.88);

INSERT INTO Listing (ListingID, PartID, SellerID, Condition, Price) VALUES
 (19, 15, 1, 'New',   99), (20, 15, 4, 'Used',  70),
 (21, 16, 2, 'New',  339),
 (22, 17, 1, 'New',  159), (23, 17, 3, 'Used', 115),
 (24, 18, 2, 'New',  329),
 (25, 19, 2, 'New',  139),
 (26, 20, 1, 'New',   79),
 (27, 21, 2, 'New',  119),
 (28, 22, 1, 'New',  139),
 (29, 24, 1, 'New',   59),
 (30, 25, 2, 'New',   49),
 (31, 26, 2, 'New',  189),
 (32, 27, 1, 'New',  179), (33, 27, 4, 'Used', 120),
 (34, 28, 2, 'New',  259), (35, 28, 3, 'Used', 195),
 (36, 29, 1, 'New',  229),
 (37, 30, 2, 'New',  349),
 (38, 31, 1, 'New',  449), (39, 31, 5, 'Used', 360),
 (40, 32, 2, 'New',  569),
 (41, 33, 1, 'New',  949),
 (42, 34, 1, 'New',  249), (43, 34, 5, 'Used', 160),
 (44, 35, 1, 'New',   55),
 (45, 36, 2, 'New',  109),
 (46, 37, 2, 'New',  149),
 (47, 38, 1, 'New',   89),
 (48, 39, 2, 'New',   45),
 (49, 40, 1, 'New',   29),
 (50, 41, 2, 'New',   32),
 (51, 42, 1, 'New',   35),
 (52, 43, 2, 'New',   55),
 (53, 44, 1, 'New',  109);
