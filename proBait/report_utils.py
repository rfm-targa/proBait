#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

"""


import os
import math
import pickle
import random
from itertools import groupby

import pandas as pd
import datapane as dp
import plotly.graph_objs as go
from plotly.offline import plot
from plotly.subplots import make_subplots


def depth_hists(depth_values):
    """
    """

    tracers = {}
    for k, v in depth_values.items():
        x_values = list(v.values())
        y_values = list(v.keys())
        tracer = go.Bar(x=x_values,
                        y=y_values,
                        hovertemplate=('<b>Coverage:<b> %{y}'
                                       '<br><b>Number of pos.:<b> %{x}'),
                        marker=dict(color='#67a9cf'),
                        showlegend=False,
                        orientation='h')
        tracers[k] = tracer

    return tracers


def missing_intervals_hists(depth_values):
    """
    """

    tracers = {}
    for k, v in depth_values.items():
        current_counts = {}
        for c, d in v.items():
            values_groups = [list(j) for i, j in groupby(d[0].values())]
            for n in values_groups:
                if n[0] == 0:
                    if len(n) in current_counts:
                        current_counts[len(n)] += 1
                    else:
                        current_counts[len(n)] = 1

        x_values = sorted(list(current_counts.keys()))
        y_values = [current_counts[j] for j in x_values]
        hist_tracer = go.Bar(x=x_values,
                             y=y_values,
                             hovertemplate=('<b>Interval size:<b> %{x}'
                                            '<br><b>Count:<b> %{y}'),
                             marker=dict(color='#67a9cf'),
                             showlegend=False)

        tracers[k] = hist_tracer

    return tracers


def depth_lines(depth_values, ordered_contigs, missing_files):
    """
    """

    shapes = {}
    tracers = {}
    for k, v in depth_values.items():
        # get uncovered intervals in the first iteration
        uncovered_file = [f for f in missing_files if k in f][0]
        with open(uncovered_file, 'rb') as infile:
            miss_regions = pickle.load(infile)

        # order contigs based on decreasing length
        contig_order = {}
        for e in ordered_contigs[k]:
            if e[0] in v:
                contig_order[e[0]] = v[e[0]]
            else:
                contig_order[e[0]] = [{i: 0 for i in range(e[1])}]

        x_values = []
        y_values = []
        hovertext = []
        shapes[k] = []
        tracers[k] = []
        # results have 0-based coordinates
        # but plots will be 1-based
        cumulative_pos = 1
        for p, c in contig_order.items():
            # get missing intervals for contig
            miss = miss_regions[p]
            # switch to 1-based coordinates for contigs
            contig_pos = 1
            # create line tracers for missing intervals in first iteration
            # coordinates are 0-based and need to be incremented to
            # get 1-based coordinates
            # create 2 tracers, one for the start coordinates and
            # another for the stop coordinates
            starts = []
            starts_hovertext = []
            stops = []
            stops_hovertext = []
            for m in miss:
                # cumulative position already includes +1
                starts.append(cumulative_pos+m[0])
                # add +1 to start to get 1-based coordinates
                starts_hovertext.append(str(m[0]+1))
                stops.append(cumulative_pos+m[1]-1)
                stops_hovertext.append(str(m[1]))

            # create tracers
            tracer_starts = go.Scattergl(x=starts,
                                         y=[0.2]*len(starts),
                                         # add +1 to start to get 1-based coordinates
                                         text=starts_hovertext,
                                         hovertemplate=('<b>Contig pos.:<b> %{text}'
                                                        '<br><b>Cumulative pos.:<b> %{x}'),
                                         showlegend=False,
                                         mode='markers',
                                         marker=dict(color='#252525', size=5, symbol='arrow-right'))

            tracer_stops = go.Scattergl(x=stops,
                                        y=[0.2]*len(stops),
                                        # add +1 to start to get 1-based coordinates
                                        text=stops_hovertext,
                                        hovertemplate=('<b>Contig pos.:<b> %{text}'
                                                       '<br><b>Cumulative pos.:<b> %{x}'),
                                        showlegend=False,
                                        mode='markers',
                                        marker=dict(color='#252525', size=5, symbol='arrow-left'))

            tracers[k].extend([tracer_starts, tracer_stops])
                # tracer_miss = go.Scattergl(x=[(cumulative_pos)+m[0], (cumulative_pos)+m[1]-1],
                #                            y=[0, 0],
                #                            # add +1 to start to get 1-based coordinates
                #                            text=[str(m[0]+1), str(m[1])],
                #                            hovertemplate=('<b>Contig pos.:<b> %{text}'
                #                                           '<br><b>Cumulative pos.:<b> %{x}'),
                #                            showlegend=False,
                #                            mode='lines',
                #                            line=dict(color='#252525', width=1))
                # tracers[k].append(tracer_miss)

            # group depth values into groups of equal sequential values
            values_groups = [list(j) for i, j in groupby(c[0].values())]
            shape_start = cumulative_pos
            for g in values_groups:
                # cumulative and contig values already include +1
                # subtract 1 from total sequence length
                hovertext.append(contig_pos)
                hovertext.append(contig_pos + (len(g) - 1))

                start_x = cumulative_pos
                stop_x = start_x + (len(g) - 1)

                # add full length to get start position of next contig
                cumulative_pos += len(g)
                contig_pos += len(g)

                x_values.extend([start_x, stop_x])
                y_values.extend([g[0], g[0]])

            shapes[k].append([shape_start, stop_x, p])
        # use Scattergl to deal with large datasets
        tracer = go.Scattergl(x=x_values,
                              y=y_values,
                              text=hovertext,
                              hovertemplate=('<b>Contig pos.:<b> %{text}'
                                             '<br><b>Cumulative pos.:<b> %{x}'
                                             '<br><b>Coverage:<b> %{y}'),
                              showlegend=False,
                              mode='lines',
                              line=dict(color='#3690c0', width=0.5))#,
                              #fill='tozeroy')
        tracers[k].append(tracer)

    return [tracers, shapes]


def coverage_table(initial2_data, final2_data, ref_ids, nr_contigs):
    """
    """

    header_values = ['Sample', 'Number of contigs', 'Total length',
                     'Initial breadth of coverage', 'Covered bases',
                     'Uncovered bases', 'Generated probes',
                     'Final breadth of coverage', 'Covered bases',
                     'Uncovered bases', 'Mean depth of coverage']

    samples = [k+' (ref)'
               if k in ref_ids
               else k
               for k, v in nr_contigs.items()]
    inputs_contigs = [v[0] for k, v in nr_contigs.items()]
    total_lengths = [v[2] for k, v in nr_contigs.items()]

    initial_cov = [round(initial2_data[k][0], 4) for k in nr_contigs]
    initial_covered = [initial2_data[k][1] for k in nr_contigs]
    initial_uncovered = [initial2_data[k][2] for k in nr_contigs]

    generated_probes = [initial2_data[k][3] for k in nr_contigs]

    final_cov = [round(final2_data[k][0], 4) for k in nr_contigs]
    final_covered = [final2_data[k][1] for k in nr_contigs]
    final_uncovered = [final2_data[k][2] for k in nr_contigs]

    # determine mean depth of coverage
    mean_depth = []
    for k in nr_contigs:
        length = nr_contigs[k][2]
        depth_counts = final2_data[k][4]
        depth_sum = sum([d*c for d, c in depth_counts.items()])
        mean = round(depth_sum/length, 4)
        mean_depth.append(mean)

    cells_values = [samples, inputs_contigs, total_lengths, initial_cov,
                    initial_covered, initial_uncovered, generated_probes,
                    final_cov, final_covered, final_uncovered, mean_depth]

    data = {'Sample': samples,
            'Number of contigs': inputs_contigs,
            'Total length': total_lengths,
            'Initial breadth of coverage': initial_cov,
            'Initial covered bases': initial_covered,
            'Initial uncovered bases': initial_uncovered,
            'Generated probes': generated_probes,
            'Final breadth of coverage': final_cov,
            'Final covered bases': final_covered,
            'Final uncovered bases': final_uncovered,
            'Mean depth of coverage': mean_depth}

    coverage_df = pd.DataFrame(data)

    coverage_table = dp.DataTable(coverage_df)

    return [coverage_table, coverage_df]


def create_shape(xref, yref, xaxis_pos, yaxis_pos,
                 line_width=1, dash_type='dashdot'):
    """
    """

    shape_tracer = dict(type='line',
                        xref=xref,
                        yref=yref,
                        x0=xaxis_pos[0], x1=xaxis_pos[1],
                        y0=yaxis_pos[0], y1=yaxis_pos[1],
                        line=dict(width=line_width,
                                  dash=dash_type))

    return shape_tracer


def create_subplots_fig(nr_rows, nr_cols, titles, specs,
                        shared_yaxes, row_heights):
    """
    """

    fig = make_subplots(rows=nr_rows, cols=nr_cols,
                        subplot_titles=titles,
                        #vertical_spacing=vertical_spacing,
                        #horizontal_spacing=horizontal_spacing,
                        shared_yaxes=shared_yaxes,
                        #column_widths=[0.9, 0.1],
                        specs=specs,
                        row_heights=row_heights)

    return fig


def create_html_report(plotly_fig, output_file, plotlyjs=True):
    """
        
        plotlyjs --> option include True, 'cdn'...check
        https://plotly.com/python/interactive-html-export/

    """

    plot(plotly_fig, filename=output_file,
         auto_open=False, include_plotlyjs=plotlyjs,
         config={"displayModeBar": False, "showTips": False})


def baits_tracer(data, ordered_contigs):
    """
    """

    # add baits scatter
    baits_x = []
    baits_y = []
    baits_labels = []
    start = 1
    for contig in ordered_contigs:
        if contig[0] in data:
            # cumulative coordinates
            current_baits = [start+int(n) for n in data[contig[0]]]
            baits_x.extend(current_baits)
            # contig coordinates
            baits_labels.extend([str(int(n)+1) for n in data[contig[0]]])

            y_values = [0] * len(current_baits)
            baits_y.extend(y_values)

        start += contig[1]

    tracer = go.Scattergl(x=baits_x, y=baits_y,
                          mode='markers',
                          marker=dict(size=4, color='#41ab5d'),
                          showlegend=False,
                          text=baits_labels,
                          hovertemplate=('<b>Contig pos.:<b> %{text}'
                                         '<br><b>Cumulative pos.:<b> %{x}'),
                          visible=True)

    return tracer


def create_scatter(x_values, y_values, mode, hovertext):
    """
    """

    tracer = go.Scattergl(x=x_values, y=y_values,
                          mode=mode,
                          #line=dict(color='black'),
                          line=dict(color='rgba(147,112,219,0.1)'),
                          showlegend=False,
                          text=hovertext,
                          hovertemplate=('%{text}'),
                          visible=True)

    return tracer


def report_specs(number_of_inputs):
    """
    """

    specs_def = [[{'type': 'table', 'rowspan': 2, 'colspan': 2},
                  None,
                  {'type': 'table', 'rowspan': 2, 'colspan': 1}],
                 [None,
                  None,
                  None],
                 [{'type': 'table', 'rowspan': 2, 'colspan': 3},
                  None,
                  None],
                 [None,
                  None,
                  None]] + \
                [[{'type': 'scatter', 'rowspan': 1, 'colspan': 1},
                  {'type': 'bar', 'rowspan': 1, 'colspan': 1},
                  {'type': 'bar', 'rowspan': 1, 'colspan': 1}]]*number_of_inputs

    return specs_def


def subplot_titles(inputs_ids):
    """
    """

    titles = [' ', '', '<b>Configuration</b>', '<b>Coverage statistics</b>']
    for s in inputs_ids:
        titles += ['<b>{0}</b>'.format(s), '', '']

    return titles


def figure_height(plot_height, table_height, config_height, total_plots):
    """
    """

    total_height = int(plot_height*total_plots + table_height*(total_plots/4) + config_height)
    plots_percentage = round((plot_height*total_plots) / total_height, 2)
    coverage_table_percentage = round((table_height*(total_plots/4)) / total_height, 2)
    summary_table_percentage = round(1 - (plots_percentage+coverage_table_percentage), 2)

    # determine row heights
    plot_height = plots_percentage / total_plots

    row_heights = [summary_table_percentage/2]*2 +\
                  [coverage_table_percentage/2]*2 +\
                  [plot_height]*(total_plots)

    return [total_height, row_heights]


def adjust_subplot_titles(plotly_fig):
    """
    """

    # adjust configuration table title position and style
    # lock table position to subplot x0 and y1 positions
    subplot12_x = plotly_fig.get_subplot(1, 3).x[0]
    subplot12_y = plotly_fig.get_subplot(1, 3).y[1]
    plotly_fig.layout.annotations[1].update(x=subplot12_x, xref='paper',
                                            xanchor='left', y=subplot12_y,
                                            font=dict(size=18))

    # adjust coverage table
    # lock to subplot x0 and y1
    subplot31_x = plotly_fig.get_subplot(3, 1).x[0]
    subplot31_y = plotly_fig.get_subplot(3, 1).y[1]
    plotly_fig.layout.annotations[2].update(x=subplot31_x, xref='paper',
                                            xanchor='left', y=subplot31_y,
                                            font=dict(size=18))

    # lock depth of coverage plots to paper x0
    for a in plotly_fig.layout.annotations[3:]:
        a.update(x=0, xref='paper', xanchor='left',
                 font=dict(size=18))

    return plotly_fig


def add_plots_traces(traces, row, col, top_x, top_y, plotly_fig):
    """
    """

    for t in traces[0]:
        plotly_fig.add_trace(t, row=row, col=col)

    plotly_fig.update_yaxes(title_text='Coverage', title_font_size=16, row=row, col=col)
    plotly_fig.update_xaxes(title_text='Position', title_font_size=16, domain=[0, 0.8], row=row, col=col)

    # scatter trace with baits start positions
    plotly_fig.add_trace(traces[1], row=row, col=col)

    # add tracer with depth values distribution
    plotly_fig.add_trace(traces[2], row=row, col=col+1)
    plotly_fig.update_yaxes(showticklabels=False, ticks='', row=row, col=col+1)
    plotly_fig.update_xaxes(showticklabels=False, ticks='', domain=[0.805, 0.9], row=row, col=col+1)

    # add tracer with missing intervals
    plotly_fig.add_trace(traces[3], row=row, col=col+2)
    plotly_fig.update_yaxes(showticklabels=False, ticks='', row=row, col=col+2)
    plotly_fig.update_xaxes(domain=[0.905, 1.0], row=row, col=col+2)

    # adjust axis range
    plotly_fig.update_xaxes(range=[-0.2, top_x], row=row, col=col)
    y_step = int(top_y/4) if int(top_y/4) > 0 else 1
    y_tickvals = list(range(0, top_y, y_step))
    if top_y not in y_tickvals:
        y_tickvals += [top_y]
    plotly_fig.update_yaxes(range=[0-top_y*0.08, top_y+(top_y*0.08)], tickvals=y_tickvals, row=row, col=col)
    plotly_fig.update_yaxes(range=[0-top_y*0.08, top_y+(top_y*0.08)], row=row, col=col+1)
    plotly_fig.update_yaxes(range=[0-top_y*0.08, top_y+(top_y*0.08)], row=row, col=col+2)

    return plotly_fig


def create_shapes(shapes_data, y_value, ref_axis):
    """
    """

    shapes_traces = []
    hidden_traces = []
    for i, s in enumerate(shapes_data):
        axis_str = '' if ref_axis == 1 else ref_axis
        xref = 'x{0}'.format(axis_str)
        yref = 'y{0}'.format(axis_str)
        # do not create line for last contig
        if s != shapes_data[-1]:
            # only create tracer for end position
            # start position is equal to end position of previous contig
            shape_tracer = create_shape(xref, yref, [s[1], s[1]], [0, y_value])
            shapes_traces.append(shape_tracer)
            # create invisible scatter to add hovertext
            hovertext = [s[2], shapes_data[i+1][2]]
            hover_str = '<b><--{0}<b><br><b>{1}--><b>'.format(*hovertext)
            y_step = int(y_value/4) if int(y_value/4) > 0 else 1
            hidden_ticks = list(range(1, y_value, y_step))
            if y_value not in hidden_ticks:
                hidden_ticks += [y_value]
        hidden_tracer = create_scatter([s[1]]*len(hidden_ticks),
                                       hidden_ticks,
                                       mode='lines',
                                       hovertext=[hover_str]*y_value)
        hidden_traces.append(hidden_tracer)

    return [shapes_traces, hidden_traces]


def add_plots_titles(plotly_fig):
    """
    """

    annotations_topy = plotly_fig.get_subplot(5, 1).yaxis.domain[1]
    annotations_boty = plotly_fig.get_subplot(5, 1).yaxis.domain[0]
    annotations_y = annotations_topy + (annotations_topy-annotations_boty) / 2.5

    plotly_fig.add_annotation(x=0, xref='paper', xanchor='left',
                              y=annotations_y, yref='paper',
                              yanchor='bottom',
                              text='<b>Depth per position</b>',
                              showarrow=False,
                              font=dict(size=18))

    plotly_fig.add_annotation(x=0.805, xref='paper', xanchor='left',
                              y=annotations_y, yref='paper',
                              yanchor='middle',
                              text='<b>Depth values<br>distribution (log)</b>',
                              showarrow=False,
                              font=dict(size=18))
    
    plotly_fig.add_annotation(x=0.905, xref='paper', xanchor='left',
                              y=annotations_y, yref='paper',
                              yanchor='middle',
                              text='<b>Missing intervals</b>',
                              showarrow=False,
                              font=dict(size=18))

    return plotly_fig


# def add_summary_text(plotly_fig, total_baits, initial_baits, bait_size,
#                      bait_offset, iter_baits, total_height):
def add_summary_text():
    """
    """

    summary_text = """# proBait report

The report has the following sections:
- **Configuration**: values passed to proBait\'s parameters.
- **Coverage statistics**: coverage statistics determined by mapping the final set of baits against each input.
- **Depth per position**: depth of coverage per position. Vertical dashed lines are contig boundaries and green markers along the x-axis are the start positions of baits that were generated to cover regions not covered by baits. Contigs are ordered based on decreasing length.
- **Depth values distribution**: distribution of depth of coverage values for each input (y-axis is shared with "Depth per position" plot in the same line).

If you have any question or wish to report an issue, please go to proBait\'s [GitHub](https://github.com/rfm-targa/proBait) repo.
"""

#     summary_text = """Quas *diva coeperat usum*; suisque, ab alii, prato. Et cornua frontes puerum,
# referam vocassent **umeris**. Dies nec suorum alis adstitit, *temeraria*,
# anhelis aliis lacunabant quoque adhuc spissatus illum refugam perterrita in
# sonus. Facturus ad montes victima fluctus undae Zancle et nulli; frigida me.
# Regno memini concedant argento Aiacis terga, foribusque audit Persephone
# serieque, obsidis cupidine qualibet Exadius.

# ```python
# utf_torrent_flash = -1;
# urlUpnp -= leakWebE - dslam;
# skinCdLdap += sessionCyberspace;
# var ascii = address - software_compile;
# webFlaming(cable, pathIllegalHtml);```

# ## Quo exul exsecrere cuique non alti caerulaque

# *Optatae o*! Quo et callida et caeleste amorem: nocet recentibus causamque.

# - Voce adduntque
# - Divesque quam exstinctum revulsus
# - Et utrique eunti
# - Vos tantum quercum fervet et nec
# - Eris pennis maneas quam
# """

    summary_text = dp.Text(summary_text)

    return summary_text
