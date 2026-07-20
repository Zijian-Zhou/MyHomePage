(function () {
  function getNested(obj, path) {
    return path.split('.').reduce(function (value, key) {
      return value && value[key] !== undefined && value[key] !== null ? value[key] : null;
    }, obj);
  }

  function drawChart(canvas, samples) {
    if (!canvas || !canvas.getContext) return;
    var ctx = canvas.getContext('2d');
    var width = canvas.width;
    var height = canvas.height;
    ctx.clearRect(0, 0, width, height);

    var paddingTop = 28;
    var paddingRight = 28;
    var paddingBottom = 28;
    var paddingLeft = 52;
    var chartWidth = width - paddingLeft - paddingRight;
    var chartHeight = height - paddingTop - paddingBottom;

    var textColor = getComputedStyle(document.documentElement).getPropertyValue('--body-quiet-color') || '#667085';
    ctx.fillStyle = textColor;
    ctx.font = '12px sans-serif';
    ctx.textAlign = 'right';
    ctx.textBaseline = 'middle';
    [100, 75, 50, 25, 0].forEach(function (tick) {
      var y = paddingTop + chartHeight - (tick / 100) * chartHeight;
      ctx.fillText(tick + '%', paddingLeft - 10, y);
    });

    ctx.strokeStyle = getComputedStyle(document.documentElement).getPropertyValue('--border-color') || '#dde3ea';
    ctx.lineWidth = 1;
    for (var i = 0; i <= 4; i += 1) {
      var y = paddingTop + (chartHeight / 4) * i;
      ctx.beginPath();
      ctx.moveTo(paddingLeft, y);
      ctx.lineTo(width - paddingRight, y);
      ctx.stroke();
    }

    function line(key, color) {
      ctx.strokeStyle = color;
      ctx.lineWidth = 2.5;
      ctx.beginPath();
      samples.forEach(function (sample, index) {
        var x = paddingLeft + (samples.length <= 1 ? chartWidth : (chartWidth / (samples.length - 1)) * index);
        var y = paddingTop + chartHeight - (Math.max(0, Math.min(100, sample[key] || 0)) / 100) * chartHeight;
        if (index === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      });
      ctx.stroke();
    }

    line('cpu', '#3a7bd5');
    line('memory', '#1f9d72');
    line('disk', '#d48a2a');
  }

  function setText(root, selector, value) {
    root.querySelectorAll(selector).forEach(function (node) {
      node.textContent = value === null || value === undefined || value === '' ? '--' : value;
    });
  }

  function formatBytes(bytes) {
    if (bytes === null || bytes === undefined || isNaN(bytes)) return '--';
    var value = Math.max(0, Number(bytes));
    var units = ['B', 'KB', 'MB', 'GB', 'TB'];
    for (var i = 0; i < units.length; i += 1) {
      if (value < 1024 || i === units.length - 1) {
        return (i === 0 ? Math.round(value) : value.toFixed(1)) + ' ' + units[i];
      }
      value /= 1024;
    }
    return '--';
  }

  document.addEventListener('DOMContentLoaded', function () {
    var root = document.querySelector('.resource-monitor');
    if (!root) return;

    var labelsNode = document.getElementById('resource-monitor-labels');
    var labels = labelsNode ? JSON.parse(labelsNode.textContent) : {};
    var endpoint = root.getAttribute('data-endpoint');
    var refreshButton = root.querySelector('[data-resource-refresh]');
    var autoInput = root.querySelector('[data-resource-auto]');
    var historyRangeInput = root.querySelector('[data-resource-history-range]');
    var chart = root.querySelector('[data-resource-chart]');
    var samples = [];
    var timer = null;
    var previousNetwork = null;

    function updateNetworkSpeed(data) {
      if (!data.network) return;
      var sent = Number(data.network.sent);
      var received = Number(data.network.received);
      var timestamp = data.timestamp ? Date.parse(data.timestamp) : Date.now();
      if (previousNetwork && !isNaN(sent) && !isNaN(received)) {
        var seconds = Math.max(1, (timestamp - previousNetwork.timestamp) / 1000);
        if (!data.network.upload_speed_display) {
          data.network.upload_speed_display = formatBytes((sent - previousNetwork.sent) / seconds) + '/s';
        }
        if (!data.network.download_speed_display) {
          data.network.download_speed_display = formatBytes((received - previousNetwork.received) / seconds) + '/s';
        }
      } else {
        data.network.upload_speed_display = data.network.upload_speed_display || '--';
        data.network.download_speed_display = data.network.download_speed_display || '--';
      }
      if (!isNaN(sent) && !isNaN(received)) {
        previousNetwork = {sent: sent, received: received, timestamp: timestamp};
      }
    }

    function updateChartValues(data) {
      var values = {
        cpu: getNested(data, 'cpu.percent'),
        memory: getNested(data, 'memory.percent'),
        disk: getNested(data, 'disk.percent')
      };
      Object.keys(values).forEach(function (key) {
        root.querySelectorAll('[data-chart-value="' + key + '"]').forEach(function (node) {
          node.textContent = values[key] === null || values[key] === undefined ? '--%' : values[key] + '%';
        });
      });
    }

    function render(data) {
      updateNetworkSpeed(data);
      setText(root, '[data-resource-updated]', data.timestamp_display);

      root.querySelectorAll('[data-resource-text]').forEach(function (node) {
        var path = node.getAttribute('data-resource-text');
        var value = getNested(data, path);
        if (path.slice(-8) === '.percent' && value !== null) value = value + '%';
        node.textContent = value === null || value === undefined || value === '' ? '--' : value;
      });

      root.querySelectorAll('[data-resource-value]').forEach(function (node) {
        var value = getNested(data, node.getAttribute('data-resource-value'));
        node.textContent = value === null || value === undefined ? '--%' : value + '%';
      });

      root.querySelectorAll('[data-resource-meter]').forEach(function (node) {
        var value = getNested(data, node.getAttribute('data-resource-meter'));
        node.style.width = Math.max(0, Math.min(100, value || 0)) + '%';
      });
      updateChartValues(data);

      if (data.available) {
        if (Array.isArray(data.history) && data.history.length) {
          samples = data.history;
        } else {
          samples.push({
            cpu: data.cpu.percent || 0,
            memory: data.memory.percent || 0,
            disk: data.disk.percent || 0
          });
          if (samples.length > 36) samples.shift();
        }
        drawChart(chart, samples);
      }
    }

    function load() {
      root.classList.add('is-loading');
      var historyMinutes = historyRangeInput ? historyRangeInput.value : '60';
      var separator = endpoint.indexOf('?') === -1 ? '?' : '&';
      fetch(endpoint + separator + 'history_minutes=' + encodeURIComponent(historyMinutes), {
        credentials: 'same-origin',
        headers: {'X-Requested-With': 'XMLHttpRequest'}
      })
        .then(function (response) {
          if (!response.ok) throw new Error(response.statusText);
          return response.json();
        })
        .then(function (data) {
          if (!data.available && data.error) {
            setText(root, '[data-resource-status]', (labels.error || 'Failed to load resource data') + ': ' + data.error);
          } else {
            render(data);
          }
        })
        .catch(function (error) {
          setText(root, '[data-resource-status]', (labels.error || 'Failed to load resource data') + ': ' + error.message);
        })
        .finally(function () {
          root.classList.remove('is-loading');
        });
    }

    function resetTimer() {
      if (timer) window.clearInterval(timer);
      timer = null;
      if (autoInput && autoInput.checked) {
        timer = window.setInterval(load, 5000);
      }
    }

    if (refreshButton) refreshButton.addEventListener('click', load);
    if (historyRangeInput) historyRangeInput.addEventListener('change', load);
    if (autoInput) autoInput.addEventListener('change', resetTimer);
    load();
    resetTimer();
  });
}());
