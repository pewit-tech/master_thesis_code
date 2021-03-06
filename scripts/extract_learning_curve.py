"""
Generates a plot with the learning curves extracted from the provided training log (Caffe output),
which is generated during training.

The log contains (among others) these lines, which are used for the learning curve extraction:
...
I0315 ... solver.cpp:331] Iteration 9400, Testing net (#0)
I0315 ... solver.cpp:398] Test net output #0: loss = 0.00676247 (* 1 = 0.00676247 loss)
...
I0315 ... solver.cpp:219] Iteration 16740 (0.509044 iter/s, 19.6447s/10 iters), loss = 0.00493241
...

----------------------------------------------------------------------------------------------------
python extract_learning_curve.py path_log path_out
----------------------------------------------------------------------------------------------------
"""

__date__   = '03/15/2016'
__author__ = 'Libor Novak'
__email__  = 'novakli2@fel.cvut.cz'


import argparse
import os
import re

import matplotlib
matplotlib.use('Agg')  # Prevents from using X interface for plotting
from matplotlib import pyplot as plt


####################################################################################################
#                                             CLASSES                                              # 
####################################################################################################

class LearningCurvePlotter(object):
	"""
	Reads the log file and extracts lines with loss function values and iteration numbers. Then it
	plots the learning curve.
	"""
	def __init__(self, path_log, title):
		"""
		Input:
			path_log:           Path to the output.txt file with Caffe learning log
			title:              Title of the plot
		"""
		super(LearningCurvePlotter, self).__init__()
		
		self.path_log = path_log
		self.title    = title

		self.iters_valid  = []
		self.losses_valid = {}
		self.iters_train  = []
		self.losses_train = {}

		self._process_log_file()
	

	def _initialize_plot(self):
		"""
		Initializes the plotting canvas.
		"""
		plt.grid()
		plt.xlabel('iteration')
		plt.ylabel('loss')
		plt.title(self.title)


	def _process_log_file(self):
		"""
		Processes the log file and extracts the loss values.
		"""
		print('-- Processing log file "%s"'%(self.path_log))

		with open(self.path_log, 'r') as infile:
			for line in infile:
				line = line.rstrip('\n')

				# We need these lines:
				# ... solver.cpp:331] Iteration 9400, Testing net (#0)
				# ... solver.cpp:398]     Test net output #0: loss_x2 = 0.00616695 (* 1 = 0.00616695 loss)
				# ... solver.cpp:398]     Test net output #1: loss_x4 = 0.0352086 (* 1 = 0.0352086 loss)
				# ... solver.cpp:398]     Test net output #2: loss_x8 = 0.0470959 (* 1 = 0.0470959 loss)
				# ... solver.cpp:219] Iteration 30 (0.256841 iter/s, 38.9347s/10 iters), loss = 0.0107558
				# ... solver.cpp:238]     Train net output #0: loss_x2 = 0.00151235 (* 1 = 0.00151235 loss)
				# ... solver.cpp:238]     Train net output #1: loss_x4 = 0.00295802 (* 1 = 0.00295802 loss)
				# ... solver.cpp:238]     Train net output #2: loss_x8 = 0.00589734 (* 1 = 0.00589734 loss)

				m = re.match(r'.* Iteration ([0-9]+), Testing net .*', line)
				if m is not None:
					self.iters_valid.append(int(m.group(1)))
					continue

				m = re.match(r'.* Test net output .* (loss_?x?[0-9]*) = ([0-9]+(\.[0-9]+)?|nan|-nan) .*', line)
				if m is not None:
					loss_name = m.group(1)
					if loss_name not in self.losses_valid.keys(): self.losses_valid[loss_name] = []
					self.losses_valid[loss_name].append(float(m.group(2)))
					continue

				m = re.match(r'.* Iteration ([0-9]+) \(.*iters.*\), loss = .*', line)
				if m is not None:
					self.iters_train.append(int(m.group(1)))
					continue

				m = re.match(r'.* Train net output .* (loss\_?x?[0-9]*) = ([0-9]+(\.[0-9]+)?|nan|-nan).*', line)
				if m is not None:
					loss_name = m.group(1)
					if loss_name not in self.losses_train.keys(): self.losses_train[loss_name] = []
					self.losses_train[loss_name].append(float(m.group(2)))
					continue

		print('-- Done processing log')


	def plot_and_save(self, path_out, skip, ylimit):
		"""
		Saves the plot to PDF and CSV.

		Input:
			path_out: Path to the output file(s) (without extension)
			skip:     Skip N iterations in the beginning in the plot
			ylimit:   Max value on the y axis - clip it (or None)
		"""
		self._initialize_plot()

		# Skip index
		si_train = 0
		si_valid = 0

		# Determine the index of the skipped iterations
		if skip > 0:
			for i in range(len(self.iters_train)):
				if self.iters_train[i] > skip: break
				si_train = i

			for i in range(len(self.iters_valid)):
				if self.iters_valid[i] > skip: break
				si_valid = i


		colors = ['#3399FF', '#FF3300', '#40BF0D', '#FFE300', '#FF33CC', '#000000']

		skeys = sorted(self.losses_train.keys())
		for i in range(len(skeys)):
			ln = skeys[i]
			plt.plot(self.iters_train[si_train:],
				     self.losses_train[ln][si_train:], label=ln+' train', color=colors[i])
		if len(self.iters_valid) > 0:
			for i in range(len(skeys)):
				ln = skeys[i]
				plt.plot(self.iters_valid[si_valid:], self.losses_valid[ln][si_valid:], 
					     label=ln+' valid', color=colors[i], linestyle='--', linewidth=2)

		# Limit axes
		xmin, xmax, ymin, ymax = plt.axis()
		ymax = ymax if ylimit is None else ylimit
		plt.axis((xmin, xmax, 0, ymax))

		plt.legend()

		plt.savefig(path_out + '.pdf', bbox_inches='tight')
		plt.savefig(path_out + '.png', bbox_inches='tight')

		# Save the values to a CSV file
		with open(path_out + '.csv', 'w') as outfile:
			outfile.write('iter')
			for key in skeys:
				outfile.write(' ' + key + '_train ' + key + '_valid')
			outfile.write('\n')

			for i in range(len(self.iters_valid)):
				try:
					i_train = self.iters_train.index(self.iters_valid[i])
					outfile.write('%d'%(self.iters_valid[i]))
					for key in skeys:
						outfile.write(' %f %f'%(self.losses_train[key][i_train],
									            self.losses_valid[key][i]))
					outfile.write('\n')

				except ValueError:
					print('Warning: Iteration "%d" not in training iterations.'%(self.iters_valid[i]))

		print('-- Plots saved to: ' + path_out)



####################################################################################################
#                                               MAIN                                               # 
####################################################################################################

def check_path(path, is_folder=False):
	"""
	Checks if the given path exists.

	Input:
		path:      Path to be checked
		is_folder: True if the checked path is a folder
	Returns:
		True if the given path exists
	"""
	if not os.path.exists(path) or (not is_folder and not os.path.isfile(path)):
		print('ERROR: Path "%s" does not exist!'%(path))
		return False

	return True


def parse_arguments():
	"""
	Parse input options of the script.
	"""
	parser = argparse.ArgumentParser(description='Plot the precision/recall curve.')
	parser.add_argument('path_log', metavar='path_log', type=str,
						help='Path to the log file with Caffe training output (mostly output.txt)')
	parser.add_argument('path_out', metavar='path_out', type=str,
						help='Path to the output file (without extension) - extensions will be ' \
						'added automatically because more files will be generated')
	parser.add_argument('--title', type=str, default='',
						help='Title of the plot')
	parser.add_argument('--skip', type=int, default=0,
						help='Skip first N iterations in the plot - this is to avoid large values '\
						'on the y axis in the plot')
	parser.add_argument('--ylimit', type=float, default=None,
						help='Clip the y axis on this value')

	args = parser.parse_args()

	if not check_path(args.path_log):
		parser.print_help()
		exit(1)

	return args


def main():
	args = parse_arguments()

	plotter = LearningCurvePlotter(args.path_log, args.title)

	plotter.plot_and_save(args.path_out, args.skip, args.ylimit)


if __name__ == '__main__':
    main()


