function CreatePDFfromHTML() {
    var contentElement = document.querySelector('.content');

    // Calculate dimensions for PDF
    var HTML_Width = contentElement.clientWidth;
    var HTML_Height = contentElement.clientHeight;
    var top_left_margin = 15;
    var PDF_Width = HTML_Width + (top_left_margin * 2);
    var PDF_Height = PDF_Width * 1;

    // Set height
    var totalPDFPages = Math.ceil(HTML_Height / PDF_Height) - 1;

    // Rendering 
    html2canvas(contentElement).then(function (canvas) {
        var imgData = canvas.toDataURL("image/jpeg", 1.0);
        var pdf = new jsPDF('p', 'pt', [PDF_Width, PDF_Height]);

        var backgroundImg = new Image();
        backgroundImg.src = '/static/css/maroon bg 2.png'; // Set the path to your background image

        backgroundImg.onload = function () {
            pdf.addImage(backgroundImg, 'JPEG', 0, 0, PDF_Width, PDF_Height); // Add background image on the first page
            pdf.addImage(imgData, 'JPEG', top_left_margin, top_left_margin, HTML_Width, HTML_Height);

            for (var i = 1; i <= totalPDFPages; i++) {
                pdf.addPage(PDF_Width, PDF_Height);
                pdf.addImage(backgroundImg, 'JPEG', 0, 0, PDF_Width, PDF_Height); // Add background image on subsequent pages
                pdf.addImage(imgData, 'JPEG', top_left_margin, -(PDF_Height * i) + (top_left_margin * 4), HTML_Width, HTML_Height);
            }

            
            pdf.save("patient_report.pdf");

            // Sending PDF to the cloud
            var pdfBlob = pdf.output('blob');
            var mrNumber = document.getElementById('mr_number').value; 

            var formData = new FormData();
            formData.append('pdf', pdfBlob, 'patient_report.pdf');
            formData.append('mr_number', mrNumber); 

            fetch('/upload_pdf', {
                method: 'POST',
                body: formData
            }).then(response => {
                if (response.ok) {
                    console.log('PDF uploaded successfully.');
                } else {
                    console.error('PDF upload failed.');
                }
            });
        }
    });
}
