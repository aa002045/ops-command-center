-- Fabricated seed data. No real customer/site names or values.

insert into clusters (id, name, site, vsan_type, node_count) values ('e4358068-5094-42e3-b096-7ab1dd30d372', 'cluster-prod-east-01', 'fake-dc-east', 'OSA', 4);
insert into clusters (id, name, site, vsan_type, node_count) values ('fbd85bb2-3ea9-4cad-bb0a-2bd221c1f226', 'cluster-prod-east-02', 'fake-dc-east', 'OSA', 4);
insert into clusters (id, name, site, vsan_type, node_count) values ('6639b51a-c9d6-408f-8f43-09c00749c12b', 'cluster-prod-west-01', 'fake-dc-west', 'OSA', 4);
insert into clusters (id, name, site, vsan_type, node_count) values ('6ef82fcc-24c4-4459-847c-eba2c1c33d0e', 'cluster-dr-01', 'fake-dc-west', 'OSA', 4);

insert into hosts (id, cluster_id, name, cpu_cores, mem_total_gb) values ('4212d2bd-3964-48b4-b0e3-07bd0415b30a', 'e4358068-5094-42e3-b096-7ab1dd30d372', 'cluster-prod-east-01-esx01', 32, 512);
insert into hosts (id, cluster_id, name, cpu_cores, mem_total_gb) values ('c0d1af12-6d86-4bb7-b100-eb9317bface3', 'e4358068-5094-42e3-b096-7ab1dd30d372', 'cluster-prod-east-01-esx02', 32, 512);
insert into hosts (id, cluster_id, name, cpu_cores, mem_total_gb) values ('ab4ec270-e09c-416f-b2e1-ca57bca64108', 'e4358068-5094-42e3-b096-7ab1dd30d372', 'cluster-prod-east-01-esx03', 32, 512);
insert into hosts (id, cluster_id, name, cpu_cores, mem_total_gb) values ('479271d0-7de0-44c6-83e1-a3d9addfee9c', 'e4358068-5094-42e3-b096-7ab1dd30d372', 'cluster-prod-east-01-esx04', 32, 512);
insert into hosts (id, cluster_id, name, cpu_cores, mem_total_gb) values ('ed74dcd0-6258-40af-8e5e-a48f2aa88b63', 'fbd85bb2-3ea9-4cad-bb0a-2bd221c1f226', 'cluster-prod-east-02-esx01', 32, 512);
insert into hosts (id, cluster_id, name, cpu_cores, mem_total_gb) values ('913e07b4-58fc-4422-ba27-1aaa68253a84', 'fbd85bb2-3ea9-4cad-bb0a-2bd221c1f226', 'cluster-prod-east-02-esx02', 32, 512);
insert into hosts (id, cluster_id, name, cpu_cores, mem_total_gb) values ('351ad0d5-0a18-424f-8090-451baad96128', 'fbd85bb2-3ea9-4cad-bb0a-2bd221c1f226', 'cluster-prod-east-02-esx03', 32, 512);
insert into hosts (id, cluster_id, name, cpu_cores, mem_total_gb) values ('af9e1b91-5759-47e6-b0e2-2b5b494ef02b', 'fbd85bb2-3ea9-4cad-bb0a-2bd221c1f226', 'cluster-prod-east-02-esx04', 32, 512);
insert into hosts (id, cluster_id, name, cpu_cores, mem_total_gb) values ('7e2aaa32-e289-4202-aa93-7e0df02795f7', '6639b51a-c9d6-408f-8f43-09c00749c12b', 'cluster-prod-west-01-esx01', 32, 512);
insert into hosts (id, cluster_id, name, cpu_cores, mem_total_gb) values ('c5a3fb23-c801-4300-8a1a-ba7b0970ef9e', '6639b51a-c9d6-408f-8f43-09c00749c12b', 'cluster-prod-west-01-esx02', 32, 512);
insert into hosts (id, cluster_id, name, cpu_cores, mem_total_gb) values ('de4a93e3-dbdf-4611-b9ff-6306599cd36c', '6639b51a-c9d6-408f-8f43-09c00749c12b', 'cluster-prod-west-01-esx03', 32, 512);
insert into hosts (id, cluster_id, name, cpu_cores, mem_total_gb) values ('b09252b0-558a-4f09-9cb5-86a3a4453781', '6639b51a-c9d6-408f-8f43-09c00749c12b', 'cluster-prod-west-01-esx04', 32, 512);
insert into hosts (id, cluster_id, name, cpu_cores, mem_total_gb) values ('793143cb-8813-4de1-9023-75c9e3c24f19', '6ef82fcc-24c4-4459-847c-eba2c1c33d0e', 'cluster-dr-01-esx01', 32, 512);
insert into hosts (id, cluster_id, name, cpu_cores, mem_total_gb) values ('4191fcf6-9e4d-4457-8114-6380a6a405a3', '6ef82fcc-24c4-4459-847c-eba2c1c33d0e', 'cluster-dr-01-esx02', 32, 512);
insert into hosts (id, cluster_id, name, cpu_cores, mem_total_gb) values ('a36db6aa-0928-497b-83d9-7afb08fd79b4', '6ef82fcc-24c4-4459-847c-eba2c1c33d0e', 'cluster-dr-01-esx03', 32, 512);
insert into hosts (id, cluster_id, name, cpu_cores, mem_total_gb) values ('773252a5-cf6d-4c04-b640-9a714e69e146', '6ef82fcc-24c4-4459-847c-eba2c1c33d0e', 'cluster-dr-01-esx04', 32, 512);

insert into datastores (id, cluster_id, name, type, total_capacity_gb) values ('f6be59e1-a835-44f8-aa38-70716bb8869e', 'e4358068-5094-42e3-b096-7ab1dd30d372', 'cluster-prod-east-01-vsan-ds', 'vSAN', 46080);
insert into datastores (id, cluster_id, name, type, total_capacity_gb) values ('a0796371-6cc6-4b41-b945-d27e5e502f69', 'fbd85bb2-3ea9-4cad-bb0a-2bd221c1f226', 'cluster-prod-east-02-vsan-ds', 'vSAN', 46080);
insert into datastores (id, cluster_id, name, type, total_capacity_gb) values ('cc471603-903a-48dc-8b10-ceff659d919f', '6639b51a-c9d6-408f-8f43-09c00749c12b', 'cluster-prod-west-01-vsan-ds', 'vSAN', 46080);
insert into datastores (id, cluster_id, name, type, total_capacity_gb) values ('01f8cf64-db08-4c06-b2d9-6a2d8924f940', '6ef82fcc-24c4-4459-847c-eba2c1c33d0e', 'cluster-dr-01-vsan-ds', 'vSAN', 46080);
