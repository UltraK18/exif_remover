// EXIF Remover Extension - Client-side functionality

document.addEventListener('DOMContentLoaded', function() {
    onUiLoaded(function() {
        enhanceDragDropArea();
        enhanceGalleryView();
    });
});

function enhanceDragDropArea() {
    const tabElement = gradioApp().getElementById('tab_exif_remover_tab');
    if (!tabElement) return;
    
    const fileInputs = tabElement.querySelectorAll('.file-preview');
    if (!fileInputs.length) return;
    
    fileInputs.forEach(fileInput => {
        fileInput.addEventListener('dragover', function(e) {
            this.classList.add('exif-remover-dragover');
        });
        
        fileInput.addEventListener('dragleave', function(e) {
            this.classList.remove('exif-remover-dragover');
        });
        
        fileInput.addEventListener('drop', function(e) {
            this.classList.remove('exif-remover-dragover');
        });
    });
}

function enhanceGalleryView() {
    const tabElement = gradioApp().getElementById('tab_exif_remover_tab');
    if (!tabElement) return;
    
    const galleryElements = tabElement.querySelectorAll('.gallery-item');
    
    galleryElements.forEach(galleryItem => {
        const img = galleryItem.querySelector('img');
        if (img) {
            img.addEventListener('load', function() {
                if (!galleryItem.querySelector('.exif-download-btn')) {
                    const downloadBtn = document.createElement('button');
                    downloadBtn.className = 'exif-download-btn';
                    downloadBtn.textContent = '다운로드';
                    downloadBtn.onclick = function(e) {
                        e.stopPropagation();
                        const link = document.createElement('a');
                        link.href = img.src;
                        link.download = 'exif_removed_' + Date.now() + '.png';
                        link.click();
                    };
                    galleryItem.appendChild(downloadBtn);
                }
            });
        }
    });
}

function onUiLoaded(callback) {
    if (typeof gradioApp !== 'function') {
        setTimeout(() => onUiLoaded(callback), 1000);
        return;
    }
    
    const interval = setInterval(function() {
        if (gradioApp().querySelector('#tab_exif_remover_tab')) {
            clearInterval(interval);
            callback();
        }
    }, 500);
}
