// 等待 jQuery 加载完成
window.addEventListener('load', function() {
    // 确保 django.jQuery 已经加载
    if (typeof django !== 'undefined' && django.jQuery) {
        (function($) {
            $(document).ready(function() {
                const bibtexInput = $('#id_bibtex_text');
                const bibtexFile = $('#id_bibtex_file');
                const form = $('form#publication_form');
                const importModal = $('#import-bibtex-modal');
                const importBtn = $('#import-bibtex-btn');
                const closeBtn = $('.close');
                const importForm = $('#import-bibtex-form');
                let pasteTimeout;

                console.log('Initialized elements:', {
                    bibtexInput: bibtexInput.length,
                    bibtexFile: bibtexFile.length,
                    importModal: importModal.length,
                    importBtn: importBtn.length,
                    closeBtn: closeBtn.length,
                    importForm: importForm.length
                });

                // 添加语言检测函数
                function getCurrentLanguage() {
                    const path = window.location.pathname;
                    return path.startsWith('/zh-hans/') ? 'zh-hans' : 'en';
                }

                // 添加消息映射
                const messages = {
                    'zh-hans': {
                        'success': '成功：',
                        'warning': '注意：',
                        'error': '错误：',
                        'input_event': '输入事件触发',
                        'bibtex_data': 'BibTeX 数据：',
                        'parsing': '正在解析 BibTeX 数据...',
                        'current_url': '当前 URL：',
                        'parse_url': '解析 URL：',
                        'parse_success': '解析成功：',
                        'edit_url': '编辑 URL：',
                        'edit_existing': '直接编辑现有条目',
                        'entry_not_found': '该条目不存在或已被删除，请修改 BibTeX key 后重试',
                        'modify_key': '修改 BibTeX key 后重试',
                        'you_can': '您可以选择：',
                        'set_field': '设置 %(field)s 为：',
                        'field_not_found': '未找到字段 #id_%(field)s',
                        'set_bibtex_key': '设置 bibtex_key 为：',
                        'bibtex_key_not_found': '未找到 BibTeX key 字段',
                        'parse_error': '解析错误：',
                        'status': '状态：',
                        'response': '响应：',
                        'parse_response_error': '解析响应失败：',
                        'parse_failed': '解析 BibTeX 数据失败',
                        'login_first': '请先登录后再试',
                        'no_permission': '没有权限执行此操作',
                        'parse_success_message': 'BibTeX 数据已成功解析并填充表单字段。请检查并确认信息无误后保存。',
                        'entry_exists': '该条目已存在，请编辑现有条目',
                        'field_updated': '字段 %(field)s 已更新',
                        'no_bibtex_data': '请先输入或上传 BibTeX 数据',
                        'import_failed': '导入失败',
                        'failed_entries': '处理失败的条目：',
                        'unsupported_field': '不支持的字段：%(field)s'
                    },
                    'en': {
                        'success': 'Success:',
                        'warning': 'Warning:',
                        'error': 'Error:',
                        'input_event': 'Input event triggered',
                        'bibtex_data': 'BibTeX data:',
                        'parsing': 'Parsing BibTeX data...',
                        'current_url': 'Current URL:',
                        'parse_url': 'Parse URL:',
                        'parse_success': 'Parse success:',
                        'edit_url': 'Edit URL:',
                        'edit_existing': 'Edit existing entry directly',
                        'entry_not_found': 'This entry does not exist or has been deleted. Please modify the BibTeX key and try again.',
                        'modify_key': 'Modify BibTeX key and try again',
                        'you_can': 'You can:',
                        'set_field': 'Set %(field)s to:',
                        'field_not_found': 'Field #id_%(field)s not found',
                        'set_bibtex_key': 'Set bibtex_key to:',
                        'bibtex_key_not_found': 'BibTeX key field not found',
                        'parse_error': 'Parse error:',
                        'status': 'Status:',
                        'response': 'Response:',
                        'parse_response_error': 'Error parsing response:',
                        'parse_failed': 'Failed to parse BibTeX data',
                        'login_first': 'Please login first',
                        'no_permission': 'You do not have permission to perform this action',
                        'parse_success_message': 'BibTeX data has been successfully parsed and form fields have been filled. Please check and confirm the information before saving.',
                        'entry_exists': 'This entry already exists, please edit the existing entry',
                        'field_updated': 'Field %(field)s updated',
                        'no_bibtex_data': 'Please enter or upload BibTeX data first',
                        'import_failed': 'Import failed',
                        'failed_entries': 'Failed entries:',
                        'unsupported_field': 'Unsupported field: %(field)s'
                    }
                };

                // 获取当前语言的消息
                function getMessage(key) {
                    const lang = getCurrentLanguage();
                    return messages[lang][key];
                }

                // 处理导入按钮点击
                importBtn.on('click', function(e) {
                    e.preventDefault();
                    importModal.show();
                });

                // 处理关闭按钮点击
                closeBtn.on('click', function() {
                    importModal.hide();
                });

                // 点击模态框外部关闭
                $(window).on('click', function(e) {
                    if ($(e.target).is(importModal)) {
                        importModal.hide();
                    }
                });

                // 处理文本输入和粘贴
                bibtexInput.on('input paste', function(e) {
                    console.log(getMessage('input_event')); // 调试日志
                    
                    // 清除之前的定时器
                    if (pasteTimeout) {
                        clearTimeout(pasteTimeout);
                    }
                    
                    // 设置新的定时器，等待粘贴完成
                    pasteTimeout = setTimeout(() => {
                        const bibtexData = $(this).val();
                        console.log(getMessage('bibtex_data'), bibtexData); // 调试日志
                    }, 500); // 500ms 延迟，确保粘贴完成
                });

                // 处理文件上传
                bibtexFile.on('change', function(e) {
                    console.log('File input changed'); // 调试日志
                    const file = e.target.files[0];
                    if (file) {
                        console.log('File selected:', file.name); // 调试日志
                        const reader = new FileReader();
                        reader.onload = function(e) {
                            const bibtexData = e.target.result;
                            console.log('File content loaded:', bibtexData); // 调试日志
                            // 将文件内容设置到输入框
                            $('#id_bibtex_text').val(bibtexData);
                            console.log('Textarea value after setting:', $('#id_bibtex_text').val()); // 调试日志
                        };
                        reader.readAsText(file);
                    }
                });

                // 处理 BibTeX 数据，移除不支持的字段
                function preprocessBibTeX(bibtexData) {
                    // 移除不支持的字段
                    const unsupportedFields = ['volume', 'number', 'pages', 'publisher'];
                    let processedData = bibtexData;
                    
                    // 处理每个条目
                    const entries = bibtexData.split('@');
                    processedData = entries.map(entry => {
                        if (!entry.trim()) return entry;
                        
                        // 移除不支持的字段
                        unsupportedFields.forEach(field => {
                            const regex = new RegExp(`\\s*${field}\\s*=\\s*{[^}]*},?\\s*`, 'g');
                            entry = entry.replace(regex, '');
                        });
                        
                        return entry;
                    }).join('@');
                    
                    return processedData;
                }

                // 处理导入表单提交
                importForm.on('submit', function(e) {
                    e.preventDefault();
                    console.log('Import form submitted'); // 调试日志
                    
                    // 获取 BibTeX 数据
                    const bibtexData = $('#id_bibtex_text').val();
                    console.log('Original BibTeX data:', bibtexData); // 调试日志
                    
                    if (!bibtexData || bibtexData.trim() === '') {
                        showAlert('error', getMessage('no_bibtex_data'));
                        return;
                    }
                    
                    // 预处理 BibTeX 数据
                    const processedBibTeX = preprocessBibTeX(bibtexData);
                    console.log('Processed BibTeX data:', processedBibTeX); // 调试日志
                    
                    // 获取当前页面的 URL
                    const currentUrl = window.location.href;
                    console.log('Current URL:', currentUrl); // 调试日志
                    
                    // 构建导入 URL
                    const importUrl = currentUrl + 'import-bibtex/';
                    console.log('Import URL:', importUrl); // 调试日志
                    
                    // 构建请求数据
                    const requestData = {
                        bibtex_text: processedBibTeX,
                        csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]').val()
                    };
                    
                    console.log('Request data:', requestData); // 调试日志
                    
                    $.ajax({
                        url: importUrl,
                        method: 'POST',
                        data: requestData,
                        success: function(response) {
                            console.log('Import success:', response); // 调试日志
                            
                            if (response.success) {
                                // 存储导入结果到 sessionStorage
                                sessionStorage.setItem('importResult', JSON.stringify({
                                    success: true,
                                    message: response.message,
                                    errors: response.errors || []
                                }));
                                
                                // 关闭模态框并刷新页面
                                importModal.hide();
                                window.location.reload();
                            } else {
                                showAlert('error', response.error || getMessage('import_failed'));
                            }
                        },
                        error: function(xhr, status, error) {
                            console.error('Import error:', error); // 调试日志
                            console.error('Status:', status);
                            console.error('Response:', xhr.responseText);
                            
                            let errorMsg = getMessage('parse_failed');
                            if (xhr.responseJSON && xhr.responseJSON.error) {
                                errorMsg = xhr.responseJSON.error;
                            } else if (xhr.status === 401) {
                                errorMsg = getMessage('login_first');
                            } else if (xhr.status === 403) {
                                errorMsg = getMessage('no_permission');
                            }
                            
                            showAlert('error', errorMsg);
                        }
                    });
                });

                // 在页面加载时检查是否有导入结果
                $(document).ready(function() {
                    const importResult = sessionStorage.getItem('importResult');
                    if (importResult) {
                        const result = JSON.parse(importResult);
                        // 清除存储的结果
                        sessionStorage.removeItem('importResult');
                        
                        // 显示成功消息
                        if (result.success) {
                            // 如果有错误，显示详细信息
                            if (result.errors && result.errors.length > 0) {
                                const errorDetails = $('<div class="error-details">')
                                    .append($('<h4>').text(getMessage('failed_entries')))
                                    .append($('<ul>').append(
                                        result.errors.map(error => {
                                            // 处理不支持的字段错误
                                            if (error.includes('unexpected keyword argument')) {
                                                const field = error.match(/'([^']+)'/)[1];
                                                return $('<li>').text(getMessage('unsupported_field').replace('%(field)s', field));
                                            }
                                            return $('<li>').text(error);
                                        })
                                    ));
                                showAlert('warning', errorDetails);
                            } else {
                                showAlert('success', result.message);
                            }
                        }
                    }
                });

                // 添加 showAlert 函数
                function showAlert(type, message) {
                    // 移除所有现有的提示消息
                    $('.alert').remove();
                    
                    const alertClass = type === 'success' ? 'alert-success' : 
                                     type === 'warning' ? 'alert-warning' : 'alert-error';
                    const messageDiv = $('<div class="alert ' + alertClass + '">')
                        .append($('<strong>').text(type === 'success' ? getMessage('success') : 
                                                  type === 'warning' ? getMessage('warning') : getMessage('error')))
                        .append(' ')
                        .append(message);
                    
                    // 只在 content div 中显示消息
                    const contentDiv = $('.app-myHomePage .content');
                    if (contentDiv.length) {
                        messageDiv.insertBefore(contentDiv.find('form#publication_form').length ? 
                            contentDiv.find('form#publication_form') : 
                            contentDiv.find('.module'));
                    }
                    
                    // 5秒后自动消失
                    setTimeout(() => messageDiv.fadeOut(() => messageDiv.remove()), 5000);
                }

                function showFeedback(element, type, message) {
                    // Remove any existing feedback
                    $('.feedback-message').remove();
                    $('.form-row').removeClass('success error');
                    
                    // Create feedback message
                    const feedback = $('<div>')
                        .addClass('feedback-message')
                        .addClass(type)
                        .text(message)
                        .hide();
                    
                    // Add feedback message after the element
                    element.after(feedback);
                    
                    // Add class to the form row
                    element.closest('.form-row').addClass(type);
                    
                    // Show feedback with animation
                    feedback.slideDown();
                    
                    // Remove feedback after 3 seconds
                    setTimeout(() => {
                        feedback.slideUp(() => {
                            feedback.remove();
                            element.closest('.form-row').removeClass(type);
                        });
                    }, 3000);
                }

                // 解析 BibTeX 数据
                function parseBibTeX(bibtexData) {
                    console.log('Parsing BibTeX data:', bibtexData);
                    
                    // 获取当前页面的 URL
                    const currentUrl = window.location.href;
                    console.log('Current URL:', currentUrl);
                    
                    // 构建解析 URL - 处理 add、change 和主列表页面
                    let parseUrl;
                    const baseUrl = window.location.pathname.split('/').slice(0, -1).join('/');
                    if (currentUrl.includes('/add/')) {
                        parseUrl = `${baseUrl}/parse-bibtex/`;
                    } else if (currentUrl.includes('/change/')) {
                        parseUrl = `${baseUrl}/parse-bibtex/`;
                    } else if (currentUrl.endsWith('/publication/')) {
                        // 如果是主列表页面，重定向到添加页面并传递 BibTeX 数据
                        const addUrl = `${baseUrl}/add/`;
                        // 将 BibTeX 数据存储在 sessionStorage 中
                        sessionStorage.setItem('pendingBibTeX', bibtexData);
                        window.location.href = addUrl;
                        return;
                    } else {
                        console.error('Invalid URL format');
                        return;
                    }
                    console.log('Parse URL:', parseUrl);
                    
                    // 构建请求数据
                    const requestData = {
                        bibtex_text: bibtexData,
                        csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]').val()
                    };
                    console.log('Request data:', requestData);
                    
                    $.ajax({
                        url: parseUrl,
                        method: 'POST',
                        data: requestData,
                        success: function(response) {
                            console.log('Raw response:', response);
                            
                            if (!response) {
                                console.error('Empty response received');
                                showFeedback(
                                    $('#id_bibtex_text'),
                                    'error',
                                    getMessage('parse_failed')
                                );
                                return;
                            }
                            
                            if (response.error) {
                                console.error('Error in response:', response.error);
                                showFeedback(
                                    $('#id_bibtex_text'),
                                    'error',
                                    response.error
                                );
                                return;
                            }
                            
                            if (response.exists) {
                                // 如果条目已存在，显示编辑链接
                                const editUrl = currentUrl.replace(/\/add\/?$/, `/${response.id}/change/`);
                                console.log('Edit URL:', editUrl);
                                
                                const message = getMessage('entry_exists');
                                const editLink = $('<a>')
                                    .attr('href', editUrl)
                                    .addClass('edit-link')
                                    .text(getMessage('edit_existing'));
                                
                                showFeedback(
                                    $('#id_bibtex_text'),
                                    'warning',
                                    $('<div>').append(message).append(editLink)
                                );
                            } else {
                                // 更新表单字段
                                const fields = {
                                    'title': response.title || '',
                                    'authors': response.authors || '',
                                    'journal': response.journal || '',
                                    'year': response.year || '',
                                    'date': response.date || '',
                                    'doi': response.doi || '',
                                    'url': response.url || '',
                                    'bibtex_key': response.bibtex_key || '',
                                    'raw_bibtex': response.raw_bibtex || '',
                                    'bibtex_type': response.bibtex_type || '',
                                    'highlighted_authors': response.highlighted_authors || '',
                                    'corresponding_authors': response.corresponding_authors || ''
                                };
                                
                                console.log('Fields to update:', fields);
                                
                                // 更新每个字段
                                Object.entries(fields).forEach(([field, value]) => {
                                    const fieldElement = $(`#id_${field}`);
                                    if (fieldElement.length) {
                                        fieldElement.val(value);
                                        console.log(`Setting ${field} to:`, value);
                                        
                                        // 显示字段更新反馈
                                        showFeedback(
                                            fieldElement,
                                            'success',
                                            getMessage('field_updated').replace('%(field)s', field)
                                        );
                                    } else {
                                        console.warn(`Field #id_${field} not found in form`);
                                    }
                                });
                                
                                // 显示总体成功消息
                                showFeedback(
                                    $('#id_bibtex_text'),
                                    'success',
                                    getMessage('parse_success_message')
                                );
                            }
                        },
                        error: function(xhr, status, error) {
                            console.error('Parse error:', error);
                            console.error('Status:', status);
                            console.error('Response:', xhr.responseText);
                            
                            let response;
                            try {
                                response = JSON.parse(xhr.responseText);
                                console.error('Parsed error response:', response);
                            } catch (e) {
                                console.error('Error parsing response:', e);
                                response = { error: getMessage('unknown_error') };
                            }
                            
                            // 显示错误消息
                            showFeedback(
                                $('#id_bibtex_text'),
                                'error',
                                response.error || getMessage('parse_failed')
                            );
                        }
                    });
                }

                function showSuccess(message) {
                    const messageDiv = $('<div class="alert alert-success">')
                        .text(message)
                        .insertBefore(form);
                    setTimeout(() => messageDiv.remove(), 5000);
                }

                function showError(message) {
                    const messageDiv = $('<div class="alert alert-error">')
                        .text(message)
                        .insertBefore(form);
                    setTimeout(() => messageDiv.remove(), 5000);
                }

                // 在页面加载时检查是否有待处理的 BibTeX 数据
                const pendingBibTeX = sessionStorage.getItem('pendingBibTeX');
                if (pendingBibTeX) {
                    // 清除存储的数据
                    sessionStorage.removeItem('pendingBibTeX');
                    // 设置输入框的值并触发解析
                    $('#id_bibtex_text').val(pendingBibTeX);
                    parseBibTeX(pendingBibTeX);
                }
            });
        })(django.jQuery);
    } else {
        console.error('django.jQuery is not available');
    }
}); 