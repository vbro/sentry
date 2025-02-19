import {InjectedRouter} from 'react-router';
import {Query} from 'history';

import ChartZoom from 'sentry/components/charts/chartZoom';
import ErrorPanel from 'sentry/components/charts/errorPanel';
import {LineChart, LineChartProps} from 'sentry/components/charts/lineChart';
import ReleaseSeries from 'sentry/components/charts/releaseSeries';
import TransitionChart from 'sentry/components/charts/transitionChart';
import TransparentLoadingMask from 'sentry/components/charts/transparentLoadingMask';
import Placeholder from 'sentry/components/placeholder';
import {IconWarning} from 'sentry/icons';
import {t} from 'sentry/locale';
import {Series} from 'sentry/types/echarts';
import {axisLabelFormatter, tooltipFormatter} from 'sentry/utils/discover/charts';
import getDynamicText from 'sentry/utils/getDynamicText';
import {Theme} from 'sentry/utils/theme';

import {transformEventStatsSmoothed} from '../../../trends/utils';

type Props = {
  errored: boolean;
  loading: boolean;
  queryExtra: Query;
  reloading: boolean;
  router: InjectedRouter;
  theme: Theme;
  series?: Series[];
  timeFrame?: {
    end: number;
    start: number;
  };
} & Omit<React.ComponentProps<typeof ReleaseSeries>, 'children' | 'queryExtra'> &
  Pick<LineChartProps, 'onLegendSelectChanged' | 'legend'>;

function Content({
  errored,
  theme,
  series: data,
  timeFrame,
  start,
  end,
  period,
  projects,
  environments,
  loading,
  reloading,
  legend,
  utc,
  queryExtra,
  router,
  onLegendSelectChanged,
}: Props) {
  if (errored) {
    return (
      <ErrorPanel>
        <IconWarning color="gray500" size="lg" />
      </ErrorPanel>
    );
  }

  const chartOptions = {
    grid: {
      left: '10px',
      right: '10px',
      top: '40px',
      bottom: '0px',
    },
    seriesOptions: {
      showSymbol: false,
    },
    tooltip: {
      trigger: 'axis' as const,
      valueFormatter: (value: number | null) => tooltipFormatter(value, 'p50()'),
    },
    xAxis: timeFrame
      ? {
          min: timeFrame.start,
          max: timeFrame.end,
        }
      : undefined,
    yAxis: {
      min: 0,
      axisLabel: {
        color: theme.chartLabel,
        // p50() coerces the axis to be time based
        formatter: (value: number) => axisLabelFormatter(value, 'p50()'),
      },
    },
  };

  const series = data
    ? data
        .map(values => {
          return {
            ...values,
            color: theme.purple300,
            lineStyle: {
              opacity: 0.75,
              width: 1,
            },
          };
        })
        .reverse()
    : [];

  const {smoothedResults} = transformEventStatsSmoothed(data, t('Smoothed'));

  const smoothedSeries = smoothedResults
    ? smoothedResults.map(values => {
        return {
          ...values,
          color: theme.purple300,
          lineStyle: {
            opacity: 1,
          },
        };
      })
    : [];

  return (
    <ChartZoom router={router} period={period} start={start} end={end} utc={utc}>
      {zoomRenderProps => (
        <ReleaseSeries
          start={start}
          end={end}
          queryExtra={queryExtra}
          period={period}
          utc={utc}
          projects={projects}
          environments={environments}
        >
          {({releaseSeries}) => (
            <TransitionChart loading={loading} reloading={reloading}>
              <TransparentLoadingMask visible={reloading} />
              {getDynamicText({
                value: (
                  <LineChart
                    {...zoomRenderProps}
                    {...chartOptions}
                    legend={legend}
                    onLegendSelectChanged={onLegendSelectChanged}
                    series={[...series, ...smoothedSeries, ...releaseSeries]}
                  />
                ),
                fixed: <Placeholder height="200px" testId="skeleton-ui" />,
              })}
            </TransitionChart>
          )}
        </ReleaseSeries>
      )}
    </ChartZoom>
  );
}

export default Content;
