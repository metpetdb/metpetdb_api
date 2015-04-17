--
-- PostgreSQL database dump
--

SET statement_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SET check_function_bodies = false;
SET client_min_messages = warning;

SET search_path = public, pg_catalog;

--
-- Data for Name: django_content_type; Type: TABLE DATA; Schema: public; Owner: metpetdb
--

COPY django_content_type (id, name, app_label, model) FROM stdin;
1	permission	auth	permission
2	group	auth	group
3	user	auth	user
4	content type	contenttypes	contenttype
5	session	sessions	session
6	site	sites	site
7	log entry	admin	logentry
8	api access	tastypie	apiaccess
9	api key	tastypie	apikey
10	group extra	api	groupextra
11	group access	api	groupaccess
12	geometry column	api	geometrycolumn
13	user	api	user
14	users role	api	usersrole
15	image type	api	imagetype
16	georeference	api	georeference
17	image format	api	imageformat
18	metamorphic grade	api	metamorphicgrade
19	metamorphic region	api	metamorphicregion
20	mineral type	api	mineraltype
21	mineral	api	mineral
22	reference	api	reference
23	region	api	region
24	rock type	api	rocktype
25	role	api	role
26	spatial ref sys	api	spatialrefsys
27	subsample type	api	subsampletype
28	admin user	api	adminuser
29	element	api	element
30	element mineral type	api	elementmineraltype
31	image reference	api	imagereference
32	oxide	api	oxide
33	oxide mineral type	api	oxidemineraltype
34	project	api	project
35	sample	api	sample
36	sample metamorphic grade	api	samplemetamorphicgrade
37	sample metamorphic region	api	samplemetamorphicregion
38	sample mineral	api	samplemineral
39	sample reference	api	samplereference
40	sample region	api	sampleregion
41	sample aliase	api	samplealiase
42	subsample	api	subsample
43	grid	api	grid
44	chemical analyses	api	chemicalanalyses
45	chemical analysis element	api	chemicalanalysiselement
46	chemical analysis oxide	api	chemicalanalysisoxide
47	image	api	image
48	image comment	api	imagecomment
49	image on grid	api	imageongrid
50	project invite	api	projectinvite
51	project member	api	projectmember
52	project sample	api	projectsample
53	sample comment	api	samplecomment
54	uploaded file	api	uploadedfile
55	xray image	api	xrayimage
\.


--
-- Name: django_content_type_id_seq; Type: SEQUENCE SET; Schema: public; Owner: metpetdb
--

SELECT pg_catalog.setval('django_content_type_id_seq', 55, true);


--
-- PostgreSQL database dump complete
--

