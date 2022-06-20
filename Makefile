
merge:
	rm -rf data/samples/01_merged/*.csv;
	python -m mt.cleaning.ais_merge config/config.json


clean:
	rm -rf data/samples/02_clean/*.csv;
	python -m mt.cleaning.data_cleaning config/config.json

maps:
	python -m mt.density.export_density_maps config/config.json


reset_sample:
	rm -rf data/samples/03_density/*.vrt;
	rm -rf data/samples/03_density/*.csv;
	rm -rf data/samples/03_density/*.tif;
	
	rm -rf data/samples/02_clean/*.csv;

	rm -rf data/samples/01_merged/*.csv;
	rm -rf data/samples/99_metadata/*.csv;
	rm -rf data/samples/99_metadata/*.json;


all:
	make reset_sample;
	make merge;
	make clean;
	make maps;