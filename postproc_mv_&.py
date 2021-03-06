import subprocess
import os
import glob
import re

PROC_ENV_KEY = None
PROC_ARG_KEY = 'PPMV&ARG'
PROC_INP_KEY = 'PPMV&INP'
PROC_NAME = 'mv'
POPENED = []

def run(argstr, inputs, env):
	global POPENED
	if len(inputs) == 0:
		print('mv requires a single path, and optionally filters for extensions.')
		return []

	patterns = [inputs[0]]
	if len(inputs) > 1:
		path_head, path_tail = os.path.split(os.path.normpath(inputs[0]))
		# print(path_head)
		# print(path_tail)

		# try take stem as preceding \..\d+\..*
		filestem = re.match(r'(?P<stem>^.*)\.\d+\..+$', path_tail)
		if filestem is not None:
			filestem = filestem.group('stem')
		else:
			filestem = path_tail
			try:
				last_point = filestem.rindex(".")
				filestem = filestem[0:last_point]
			except:
				pass

		patterns = [os.path.join(path_head, filestem+extension) for extension in inputs[1:]]

	cmd = ['mkdir', '-p', argstr]
	print(' '.join(cmd))
	subprocess.run(cmd)

	POPENED = []
	for pattern in patterns:
		print(pattern)

		matchedfiles = glob.glob(pattern)
		for mfile in matchedfiles:
			cmd = ['mv', mfile, argstr]
			print(' '.join(cmd))
			
			# the move command is detached
			POPENED.append(subprocess.Popen(cmd))
			
	return patterns