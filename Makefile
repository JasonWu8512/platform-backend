fmt:
	export file=zero/dataTool/command.py;\
	export file1=zero/dataTool/apiRequest.py;\
	export file2=zero/api/views/dataTool.py;\
	export file3=zero/utils/super_requests.py;\
	autoflake --recursive --remove-all-unused-imports --in-place $${file} $${file1} $${file2} $${file3} && isort $${file} $${file1} $${file2} $${file3} && black $${file} $${file1} $${file2} $${file3} -l 120
