/*
Anki Simulator Add-on for Anki

Copyright (C) 2020  GiovanniHenriksen https://github.com/giovannihenriksen
Copyright (C) 2020  Aristotelis P. https://glutanimate.com/

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see https://www.gnu.org/licenses/.
*/

let chart;
let ctx;

function initializeChart(isNightMode = False) {

  if (isNightMode) {
    Chart.defaults.global.defaultFontColor = "white";
    Chart.defaults.scale.gridLines.color = "rgba(255, 255, 255, 0.2)";
    Chart.defaults.scale.gridLines.zeroLineColor = "rgba(255, 255, 255, 0.25)";
    Chart.defaults.global.tooltips.backgroundColor = "rgba(255, 255, 255, 0.9)";
    Chart.defaults.global.tooltips.bodyFontColor = "rgba(0, 0, 0, 1)";
    Chart.defaults.global.tooltips.titleFontColor = "rgba(0, 0, 0, 1)";
    Chart.defaults.global.tooltips.footerFontColor = "rgba(0, 0, 0, 1)";
  }

  ctx = document.getElementById("chart");
  chart = new Chart(ctx, {
    type: "line",
    options: {
      responsive: true,
      maintainAspectRatio: false,
      tooltips: {
        mode: "nearest",
        intersect: false,
        callbacks: {
            afterLabel: function(tooltipItem, data) {
               var datasetData = data.datasets[tooltipItem.datasetIndex].data
               var dayIndex = tooltipItem.index
               var dayData = datasetData[dayIndex]
               return 'Day: ' + dayData.dayNumber
               + '\nTotal repetitions until this day: ' + dayData.accumulate
               + '\nAverage number of repetitions until this day: ' + Math.round(dayData.average)
               + '\nAmount of cards mature (interval higher than 21 days): ' + dayData.matureCount + '/' + dayData.totalNumberOfCards + ' (' + Math.round(100 * dayData.matureCount / dayData.totalNumberOfCards) + '%)';
            }
         }
      },
      hover: {
        mode: "nearest",
        intersect: false
      },
      scales: {
        xAxes: [
          {
            type: "time",
            distribution: "linear",
            time: {
              minUnit: "day"
            },
            position: "bottom",
            ticks: {
              maxTicksLimit: 12,
              fontSize: 14
            }
          }
        ],
        yAxes: [
          {
            ticks: {
              fontSize: 14,
              beginAtZero: true,
              precision: 0
            },
            scaleLabel: {
              display: true,
              labelString: "Number of repetitions",
              fontSize: 16,
              padding: 12
            }
          }
        ]
      }
    }
  });
}

function newDataSet(dataAsJSON) {
  let chartColors = [
    "rgb(255, 99, 132)",
    "rgb(255, 159, 64)",
    "rgb(255, 205, 86)",
    "rgb(75, 192, 192)",
    "rgb(54, 162, 235)",
    "rgb(153, 102, 255)",
    "rgb(201, 203, 207)"
  ];
  let color = chartColors[chart.data.datasets.length % chartColors.length];
  let parsedData = JSON.parse(dataAsJSON)
  let label = parsedData[0]
  let data = parsedData[1]
  let newDataset = {
    label: label,
    backgroundColor: color,
    borderColor: color,
    data: data,
    fill: false,
    pointRadius: ((parsedData.length > 1) ? 0 : 4),
    pointHoverRadius: 4
  };
  chart.data.datasets.push(newDataset);
  chart.update();
}

function clearLastDataset() {
  chart.data.datasets.splice(-1, 1);
  chart.update();
}
