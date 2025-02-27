let selectedPDF = null;
let pdfCounter = 1;
let generateBtn;

// Initialize the UI when the document is fully loaded
document.addEventListener('DOMContentLoaded', function() {
    generateBtn = document.getElementById('generate-btn');
    
    // Initial check for empty gallery
    checkEmptyGallery();
    
    // Add event listener for file upload
    document.getElementById('pdf-upload').addEventListener('change', handleFileUpload);
    
    // Event listener for Enter key in chat input
    document.getElementById('chat-input-field').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });
    
    // Clear the file input when selecting a new file
    document.getElementById('pdf-upload').addEventListener('click', function() {
        this.value = '';
    });
});

// Function to check if gallery is empty
function checkEmptyGallery() {
    const gallery = document.querySelector('.pdf-gallery');
    const noFilesMessage = document.getElementById('no-pdfs-message');
    
    if (gallery.children.length === 0) {
        noFilesMessage.style.display = 'block';
        generateBtn.disabled = true;
    } else {
        noFilesMessage.style.display = 'none';
    }
}

function selectPDF(element, pdfName) {
    // Prevent selection if clicking on remove button (handled by event bubbling)
    if (event && event.target.closest('.remove-btn')) {
        return;
    }
    
    // Remove selection from all cards
    document.querySelectorAll('.pdf-card').forEach(card => {
        card.classList.remove('selected');
    });
    
    // Select current card
    element.classList.add('selected');
    selectedPDF = pdfName;
    
    // Enable generate button
    generateBtn.disabled = false;
    
    // Set current PDF name
    document.getElementById('current-pdf').textContent = pdfName;
    
    // Add click event to generate button
    generateBtn.onclick = generateSummary;
}

function removePDF(event, element) {
    event.stopPropagation(); // Prevent the card's click event from firing
    
    // Get the PDF name for potential future use (e.g., removing from storage)
    const pdfTitle = element.querySelector('.pdf-title').textContent;
    
    // Check if this is the selected PDF
    const isSelected = element.classList.contains('selected');
    
    // Remove the element from the DOM
    element.remove();
    
    // If this was the selected PDF, disable the generate button
    if (isSelected) {
        generateBtn.disabled = true;
        selectedPDF = null;
        document.getElementById('current-pdf').textContent = '';
    }
    
    // Check if gallery is now empty
    checkEmptyGallery();
    
    console.log(`Removed PDF: ${pdfTitle}`);
}

function generateSummary() {
    if (!selectedPDF) {
        alert('Please select a PDF first');
        return;
    }
    
    // Show loading indicator
    document.getElementById('loading-summary').style.display = 'flex';
    document.getElementById('summary-content').innerHTML = '';
    
    // Switch to summary screen
    goToSummaryScreen();
    // Request summary from server
    fetch('/generate', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            pdf_name: selectedPDF
        })
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(data => {
                throw new Error(data.error || 'Network response was not ok');
            });
        }
        return response.json();
    })
    .then(data => {
        // Hide loading indicator
        document.getElementById('loading-summary').style.display = 'none';
        
        // Display the summary
        document.getElementById('summary-content').innerHTML = data.summary;
    })
    .catch(error => {
        console.error('Error:', error);
        document.getElementById('loading-summary').style.display = 'none';
        document.getElementById('summary-content').innerHTML = '<p class="error">Error generating summary. Please try again.</p>';
    });
}

function goToSummaryScreen() {
    document.getElementById('screen1').classList.remove('active');
    document.getElementById('screen2').classList.add('active');
}

function goBack() {
    document.getElementById('screen2').classList.remove('active');
    document.getElementById('screen1').classList.add('active');
}

function sendMessage() {
    const inputField = document.getElementById('chat-input-field');
    const message = inputField.value.trim();
    
    if (message) {
        const chatMessages = document.getElementById('chat-messages');
        
        // Add user message
        chatMessages.innerHTML += `
            <div class="message message-user">
                <div class="message-content">${message}</div>
            </div>
        `;
        
        // Add loading message
        const loadingMsgId = 'loading-msg-' + Date.now();
        chatMessages.innerHTML += `
            <div class="message message-ai" id="${loadingMsgId}">
                <div class="message-content">
                    <div class="typing-indicator">
                        <span></span>
                        <span></span>
                        <span></span>
                    </div>
                </div>
            </div>
        `;
        
        // Clear input field
        inputField.value = '';
        
        // Auto scroll to bottom
        chatMessages.scrollTop = chatMessages.scrollHeight;
        
        // Make API call to Flask backend
        fetch('/ask', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                question: message,
                pdf_name: selectedPDF
            })
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(data => {
                    throw new Error(data.error || 'Network response was not ok');
                });
            }
            return response.json();
        })
        .then(data => {
            // Remove loading message
            document.getElementById(loadingMsgId).remove();
            
            // Add AI response
            chatMessages.innerHTML += `
                <div class="message message-ai">
                    <div class="message-content">${data.response}</div>
                </div>
            `;
            chatMessages.scrollTop = chatMessages.scrollHeight;
        })
        .catch(error => {
            console.error('Error:', error);
            
            // Remove loading message
            document.getElementById(loadingMsgId).remove();
            
            // Add error message
            chatMessages.innerHTML += `
                <div class="message message-ai">
                    <div class="message-content">Sorry, there was an error processing your request.</div>
                </div>
            `;
            chatMessages.scrollTop = chatMessages.scrollHeight;
        });
    }
}

// First, add this to your HTML head section
// <script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.4.120/pdf.min.js"></script>
// <script>pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.4.120/pdf.worker.min.js';</script>

function handleFileUpload(e) {
  if (e.target.files.length > 0) {
      const file = e.target.files[0];
      if (file.type !== 'application/pdf') {
          alert('Please upload a PDF file');
          return;
      }
      
      const fileName = file.name;
      
      // Generate PDF thumbnail preview before uploading
      generatePDFThumbnail(file).then(thumbnailCanvas => {
          // Create FormData object to send file
          const formData = new FormData();
          formData.append('pdf_file', file);
          
          // Show loading indicator
          const pdfGallery = document.querySelector('.pdf-gallery');
          const loadingCard = document.createElement('div');
          loadingCard.className = 'pdf-card loading';
          loadingCard.innerHTML = `
              <div class="pdf-thumbnail">
                  <div class="loading-spinner"></div>
              </div>
              <div class="pdf-info">
                  <h3 class="pdf-title">Uploading ${fileName}...</h3>
              </div>
          `;
          pdfGallery.prepend(loadingCard);
          
          // Upload file to server
          fetch('/upload_pdf', {
              method: 'POST',
              body: formData
          })
          .then(response => {
              if (!response.ok) {
                  throw new Error(`Server error: ${response.status} ${response.statusText}`);
              }
              return response.json();
          })
          .then(data => {
              console.log('Upload successful:', data);
              
              // Remove loading card
              loadingCard.remove();
              
              // Create new PDF card with the thumbnail
              const newCard = document.createElement('div');
              newCard.className = 'pdf-card';
              
              // Create thumbnail container
              const thumbnailDiv = document.createElement('div');
              thumbnailDiv.className = 'pdf-thumbnail';
              
              // Add the canvas preview instead of static image
              if (thumbnailCanvas) {
                  thumbnailCanvas.style.maxWidth = '100%';
                  thumbnailCanvas.style.height = 'auto';
                  thumbnailDiv.appendChild(thumbnailCanvas);
              } else {
                  // Fallback to static image if preview generation fails
                  const fallbackImg = document.createElement('img');
                  fallbackImg.src = '/static/img/pdf-icon.png';
                  fallbackImg.alt = 'PDF';
                  thumbnailDiv.appendChild(fallbackImg);
              }
              
              // Create info div
              const infoDiv = document.createElement('div');
              infoDiv.className = 'pdf-info';
              infoDiv.innerHTML = `
                  <h3 class="pdf-title">${fileName}</h3>
                  <p class="pdf-details">Uploaded just now</p>
              `;
              
              // Create remove button
              const removeBtn = document.createElement('button');
              removeBtn.className = 'remove-btn';
              removeBtn.textContent = '×';
              removeBtn.onclick = function(event) {
                  event.stopPropagation();
                  removePDF(event, newCard);
              };
              
              // Assemble the card
              newCard.appendChild(thumbnailDiv);
              newCard.appendChild(infoDiv);
              newCard.appendChild(removeBtn);
              
              // Add click event to select this PDF
              newCard.onclick = function() {
                  selectPDF(this, fileName);
              };
              
              // Add to gallery
              pdfGallery.prepend(newCard);
              
              // Update empty gallery message
              checkEmptyGallery();
              
              // Auto-select the new PDF
              selectPDF(newCard, fileName);
          })
          .catch(error => {
              console.error('Detailed error:', error);
              loadingCard.remove();
              alert(`Error uploading file: ${error.message}`);
          });
      }).catch(error => {
          console.error('Error generating PDF thumbnail:', error);
          // Continue with upload even if thumbnail generation fails
          // (The same code as above would be repeated here, but using the static image)
          // To avoid duplication, you could refactor the upload process into a separate function
      });
  }
}

// Function to generate PDF preview thumbnail
function generatePDFThumbnail(file) {
  return new Promise((resolve, reject) => {
      const reader = new FileReader();
      
      reader.onload = function(event) {
          const pdfData = new Uint8Array(event.target.result);
          
          // Load PDF document using PDF.js
          pdfjsLib.getDocument({ data: pdfData }).promise.then(pdf => {
              // Get the first page
              return pdf.getPage(1);
          }).then(page => {
              // Set scale for thumbnail (adjust as needed)
              const scale = 0.5;
              const viewport = page.getViewport({ scale: scale });
              
              // Create canvas for thumbnail
              const canvas = document.createElement('canvas');
              const context = canvas.getContext('2d');
              canvas.height = viewport.height;
              canvas.width = viewport.width;
              
              // Render the PDF page to canvas
              const renderContext = {
                  canvasContext: context,
                  viewport: viewport
              };
              
              page.render(renderContext).promise.then(() => {
                  resolve(canvas);
              }).catch(error => {
                  console.error('Error rendering PDF page:', error);
                  reject(error);
              });
          }).catch(error => {
              console.error('Error loading PDF:', error);
              reject(error);
          });
      };
      
      reader.onerror = function(error) {
          console.error('Error reading file:', error);
          reject(error);
      };
      
      // Read the file as an ArrayBuffer
      reader.readAsArrayBuffer(file);
  });
}
