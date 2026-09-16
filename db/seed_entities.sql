-- Fabricated seed data. No real customer/site names or values.

insert into clusters (id, name, site, vsan_type, node_count) values ('cda9e1ab-2de0-5758-9426-af6716f27361', 'cluster-prod-east-01', 'fake-dc-east', 'OSA', 4);
insert into clusters (id, name, site, vsan_type, node_count) values ('3a07cdb1-d4e1-5c6f-a317-ec38ce02a224', 'cluster-prod-east-02', 'fake-dc-east', 'OSA', 4);
insert into clusters (id, name, site, vsan_type, node_count) values ('354eab6d-b791-553e-98d4-1740bd629a71', 'cluster-prod-west-01', 'fake-dc-west', 'OSA', 4);
insert into clusters (id, name, site, vsan_type, node_count) values ('a9b62aad-5e00-5e6a-8feb-a1e62991190f', 'cluster-dr-01', 'fake-dc-west', 'OSA', 4);

insert into hosts (id, cluster_id, name, cpu_cores, mem_total_gb) values ('591e660f-d6e3-51a0-947c-e788e1318c59', 'cda9e1ab-2de0-5758-9426-af6716f27361', 'cluster-prod-east-01-esx01', 32, 512);
insert into hosts (id, cluster_id, name, cpu_cores, mem_total_gb) values ('3c923de6-989e-546c-ad99-34eb3857b825', 'cda9e1ab-2de0-5758-9426-af6716f27361', 'cluster-prod-east-01-esx02', 32, 512);
insert into hosts (id, cluster_id, name, cpu_cores, mem_total_gb) values ('8078bd54-2844-5a71-9b48-41773152cc1e', 'cda9e1ab-2de0-5758-9426-af6716f27361', 'cluster-prod-east-01-esx03', 32, 512);
insert into hosts (id, cluster_id, name, cpu_cores, mem_total_gb) values ('85b5f7fb-7505-5831-9ad7-e281aa4782cb', 'cda9e1ab-2de0-5758-9426-af6716f27361', 'cluster-prod-east-01-esx04', 32, 512);
insert into hosts (id, cluster_id, name, cpu_cores, mem_total_gb) values ('16dd56a1-10a4-5c1e-8723-704717bafb9b', '3a07cdb1-d4e1-5c6f-a317-ec38ce02a224', 'cluster-prod-east-02-esx01', 32, 512);
insert into hosts (id, cluster_id, name, cpu_cores, mem_total_gb) values ('198ba3b8-9791-5e8d-ac23-9322c23edc5c', '3a07cdb1-d4e1-5c6f-a317-ec38ce02a224', 'cluster-prod-east-02-esx02', 32, 512);
insert into hosts (id, cluster_id, name, cpu_cores, mem_total_gb) values ('666211c8-0cea-5412-b955-481305d4cc61', '3a07cdb1-d4e1-5c6f-a317-ec38ce02a224', 'cluster-prod-east-02-esx03', 32, 512);
insert into hosts (id, cluster_id, name, cpu_cores, mem_total_gb) values ('854971a3-96d1-5d9a-9903-27e72408036f', '3a07cdb1-d4e1-5c6f-a317-ec38ce02a224', 'cluster-prod-east-02-esx04', 32, 512);
insert into hosts (id, cluster_id, name, cpu_cores, mem_total_gb) values ('c8cec1d5-2ee0-5da5-b1a6-bb1365eb8078', '354eab6d-b791-553e-98d4-1740bd629a71', 'cluster-prod-west-01-esx01', 32, 512);
insert into hosts (id, cluster_id, name, cpu_cores, mem_total_gb) values ('cd524d2a-aede-5e16-94d6-46c1799cabdc', '354eab6d-b791-553e-98d4-1740bd629a71', 'cluster-prod-west-01-esx02', 32, 512);
insert into hosts (id, cluster_id, name, cpu_cores, mem_total_gb) values ('922aad91-da2f-5289-aac6-4918684887df', '354eab6d-b791-553e-98d4-1740bd629a71', 'cluster-prod-west-01-esx03', 32, 512);
insert into hosts (id, cluster_id, name, cpu_cores, mem_total_gb) values ('4fb78e1c-c765-5518-9be7-d5637c3ab380', '354eab6d-b791-553e-98d4-1740bd629a71', 'cluster-prod-west-01-esx04', 32, 512);
insert into hosts (id, cluster_id, name, cpu_cores, mem_total_gb) values ('1626cdc7-1185-5497-9cc1-7bfc939b78e2', 'a9b62aad-5e00-5e6a-8feb-a1e62991190f', 'cluster-dr-01-esx01', 32, 512);
insert into hosts (id, cluster_id, name, cpu_cores, mem_total_gb) values ('47babaf2-2327-5223-ad81-05de225673b3', 'a9b62aad-5e00-5e6a-8feb-a1e62991190f', 'cluster-dr-01-esx02', 32, 512);
insert into hosts (id, cluster_id, name, cpu_cores, mem_total_gb) values ('94a1a75b-9d2d-5a36-a7de-25f1ea532369', 'a9b62aad-5e00-5e6a-8feb-a1e62991190f', 'cluster-dr-01-esx03', 32, 512);
insert into hosts (id, cluster_id, name, cpu_cores, mem_total_gb) values ('5edebb1b-8d69-5b7c-84b4-26b9a2c58af7', 'a9b62aad-5e00-5e6a-8feb-a1e62991190f', 'cluster-dr-01-esx04', 32, 512);

insert into datastores (id, cluster_id, name, type, total_capacity_gb) values ('3a6c166d-37fa-5cda-adad-777eb4567f37', 'cda9e1ab-2de0-5758-9426-af6716f27361', 'cluster-prod-east-01-vsan-ds', 'vSAN', 46080);
insert into datastores (id, cluster_id, name, type, total_capacity_gb) values ('f1a6081a-48e3-56db-936e-f49af9832cb1', '3a07cdb1-d4e1-5c6f-a317-ec38ce02a224', 'cluster-prod-east-02-vsan-ds', 'vSAN', 46080);
insert into datastores (id, cluster_id, name, type, total_capacity_gb) values ('18b90679-ba14-5785-bca6-c3cc1e3ad587', '354eab6d-b791-553e-98d4-1740bd629a71', 'cluster-prod-west-01-vsan-ds', 'vSAN', 46080);
insert into datastores (id, cluster_id, name, type, total_capacity_gb) values ('77059140-e829-5d12-90bd-2d2ebd9c436c', 'a9b62aad-5e00-5e6a-8feb-a1e62991190f', 'cluster-dr-01-vsan-ds', 'vSAN', 46080);
