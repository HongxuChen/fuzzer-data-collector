import matplotlib.pyplot as plt
import numpy as np
import scipy.stats
import os


def mean_confidence_interval(data, confidence):
    a = 1.0 * np.array(data)
    n = len(a)
    m, se = np.mean(a), scipy.stats.sem(a)
    h = se * scipy.stats.t.ppf((1+confidence)/2., n-1)
    return m, m-h, m+h


def row_to_col(rows):
    return [*zip(*rows)]


def mkdirs(path):
    if not os.path.exists(path):
        os.makedirs(path)


def display_bucket(bucket):
    if bucket[0] == 's':
        return 'sec'
    elif bucket[0] == 'm':
        return 'min'
    elif bucket[0] == 'h':
        return 'hour'
    else:
        # wrong bucket encoding
        return 'invalid_value'


def get_step(misc_dict):
    step = 1
    if misc_dict['bucket'] == 'm':
        step = 60
    elif misc_dict['bucket'] == 'h':
        step = 3600

    return step


# align data files
def align_data(fuzzer_dict, misc_dict):

    fuzzer_name = fuzzer_dict['name']
    data_files = fuzzer_dict['data_files']
    out_dir = misc_dict['out_dir']
    aligned_dir = out_dir + "/aligned/" + fuzzer_name + '/'
    max_slot = int(misc_dict['max_time']) * 3600

    mkdirs(aligned_dir)

    new_data_files = []

    print("[*] aligning data for {}".format(fuzzer_name))

    for (j, data_file) in enumerate(data_files):
        slots = []
        vals = []
        with open(data_file) as df:
            lines = df.readlines()

            for line in lines:
                tokens = line.split(":")
                slot = int(tokens[0])
                val = int(tokens[1])
                if slot > max_slot:
                    break
                slots.append(slot)
                vals.append(val)

        slot_idx = 0
        new_vals = []

        for i in range(0, max_slot):
            if i > slots[slot_idx]:
                slot_idx = min(len(slots)-1, slot_idx + 1)
            new_vals.append(vals[slot_idx])

        new_data_file = aligned_dir + str(j) + ".txt"
        with open(new_data_file, "w") as out_file:
            for val in new_vals:
                out_file.write(str(val)+'\n')

        new_data_files.append(new_data_file)

    fuzzer_dict['data_files'] = new_data_files


# plot for every data file of the fuzzer; n is the id for the figure
def detailed_plot(fuzzer_dict, misc_dict, n):
    fig = plt.figure(n)
    ax = fig.add_subplot(111)

    data_files = fuzzer_dict['data_files']
    fuzzer_name = fuzzer_dict['name']
    print('[*] generating detailed plots for {}'.format(fuzzer_name))

    step = get_step(misc_dict)

    for (i, data_file) in enumerate(data_files):
        with open(data_file) as df:
            lines = df.readlines()
            ys = [int(x) for x in lines]
            ys = ys[0::step]
            bins = range(0, len(ys))
            ax.plot(bins, ys, label=fuzzer_name + str(i))

            out_dir = misc_dict['out_dir'] + '/detailed/' + fuzzer_name + '/'
            mkdirs(out_dir)
            base_filename = out_dir + misc_dict["project"] + "_detailed" + misc_dict["file_postfix"]
            filename_pdf = base_filename + '.pdf'
            filename_png = base_filename + '.png'

            ax.set(xlabel='time ({})'.format(display_bucket(misc_dict['bucket'])), ylabel=misc_dict['ylabel'])
            ax.legend()
            fig.savefig(filename_pdf)
            fig.savefig(filename_png)


# add plots to ax; write the computed data out
def plot_files(fuzzer_dict, misc_dict, ax):
    entire_data_rows = []

    data_files = fuzzer_dict['data_files']
    fuzzer_name = fuzzer_dict['name']

    print('[*] generating overall plots for {}'.format(fuzzer_name))

    for data_file in data_files:
        data_row = []
        with open(data_file) as df:
            lines = df.readlines()
            for line in lines:
                data_row.append(int(line))
        entire_data_rows.append(data_row)

    entire_data_col = row_to_col(entire_data_rows)

    fuzzer_dict['final_vals'] = entire_data_col[-1]

    means = []
    mins = []
    maxs = []
    bins = []

    for col in entire_data_col:
        mean, min_, max_ = mean_confidence_interval(col, misc_dict['confidence_lvl'])
        means.append(mean)
        mins.append(max(min_, 0))
        maxs.append(max_)

    data_dir = misc_dict['out_dir'] + '/' + 'stat_data/'
    mkdirs(data_dir)

    with open(data_dir + fuzzer_name + "-mean-confi.txt", "w") as df:
        for (idx, mean) in enumerate(means):
            df.write("{},{},{}\n".format(mean, mins[idx], maxs[idx]))
            bins.append(idx)

    set_line_color = 'line_color' in fuzzer_dict
    set_line_style = 'line_style' in fuzzer_dict

    step = get_step(misc_dict)

    bins = [int(x/step) for x in bins[0::step]]

    if set_line_color and set_line_style:
        ax.plot(bins[0:], means[0::step], label=fuzzer_name, linestyle=fuzzer_dict['line_style'], color=fuzzer_dict['line_color'])
        ax.fill_between(bins[0:], mins[0::step], maxs[0::step], facecolor=fuzzer_dict['line_color'], alpha=0.2)
    elif set_line_color:
        ax.plot(bins[0:], means[0::step], label=fuzzer_name, color=fuzzer_dict['line_color'])
        ax.fill_between(bins[0:], mins[0::step], maxs[0::step], facecolor=fuzzer_dict['line_color'], alpha=0.2)
    elif set_line_style:
        ax.plot(bins[0:], means[0::step], label=fuzzer_name, linestyle=fuzzer_dict['line_style'])
        ax.fill_between(bins[0:], mins[0::step], maxs[0::step], alpha=0.2)
    else:
        ax.plot(bins[0:], means[0::step], label=fuzzer_name)
        ax.fill_between(bins[0:], mins[0::step], maxs[0::step], alpha=0.2)


def student_t_test(filename, open_mode, fuzzers_dict):
    with open(filename, open_mode) as gsf:
        checked = []
        gsf.write("### Student's t test ###\n")
        for fuzzer_name1 in fuzzers_dict:
            for fuzzer_name2 in fuzzers_dict:
                if not fuzzer_name1 == fuzzer_name2 and not (fuzzer_name1, fuzzer_name2) in checked:
                    f1 = fuzzers_dict[fuzzer_name1]
                    f2 = fuzzers_dict[fuzzer_name2]
                    checked.append((fuzzer_name1, fuzzer_name2))
                    checked.append((fuzzer_name2, fuzzer_name1))

                    p_value = scipy.stats.ttest_ind(f1['final_vals'], f2['final_vals'])[1]

                    gsf.write("pvalue: {} --- {} : {}\n".format(fuzzer_name1, fuzzer_name2, p_value))
        gsf.write("\n")


def mw_u_test(filename, open_mode, fuzzers_dict):
    with open(filename, open_mode) as gsf:
        checked = []
        gsf.write("### Mann Whitney u test ###\n")
        for fuzzer_name1 in fuzzers_dict:
            for fuzzer_name2 in fuzzers_dict:
                if not fuzzer_name1 == fuzzer_name2 and not (fuzzer_name1, fuzzer_name2) in checked:
                    f1 = fuzzers_dict[fuzzer_name1]
                    f2 = fuzzers_dict[fuzzer_name2]
                    checked.append((fuzzer_name1, fuzzer_name2))
                    checked.append((fuzzer_name2, fuzzer_name1))

                    p_value = scipy.stats.mannwhitneyu(f1['final_vals'], f2['final_vals'])[1]

                    gsf.write("pvalue: {} --- {} : {}\n".format(fuzzer_name1, fuzzer_name2, p_value))
        gsf.write("\n")


def generate_plots(fuzzers_dict, misc_dict):
    fig = plt.figure(len(fuzzers_dict))
    ax = fig.add_subplot(111)

    for (n, fuzzer_name) in enumerate(fuzzers_dict):
        fuzzer_dict = fuzzers_dict[fuzzer_name]
        align_data(fuzzer_dict, misc_dict)
        detailed_plot(fuzzer_dict, misc_dict, n)
        plot_files(fuzzer_dict, misc_dict, ax)

    out_dir = misc_dict['out_dir'] + '/'
    base_filename = out_dir + misc_dict["project"] + "_overall" + misc_dict["file_postfix"]
    filename_pdf = base_filename + '.pdf'
    filename_png = base_filename + '.png'
    general_stats_file = out_dir + misc_dict["project"] + "_overall_stats" + misc_dict["file_postfix"] + ".txt"

    student_t_test(general_stats_file, 'w', fuzzers_dict)

    mw_u_test(general_stats_file, 'a', fuzzers_dict)

    ax.set(xlabel='time ({})'.format(display_bucket(misc_dict['bucket'])), ylabel=misc_dict['ylabel'])
    ax.legend()
    fig.savefig(filename_pdf)
    fig.savefig(filename_png)
