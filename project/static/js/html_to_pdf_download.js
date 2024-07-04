function CreatePDFfromHTML() {
    var contentElement = document.getElementById('content');

    // Calculate dimensions for PDF
    var HTML_Width = contentElement.clientWidth;
    var HTML_Height = contentElement.clientHeight;
    var top_left_margin = 15;
    var PDF_Width = HTML_Width + (top_left_margin * 2);
    var PDF_Height = PDF_Width * 1.5;

    var canvas = document.createElement('canvas');
    var context = canvas.getContext('2d');
    canvas.width = HTML_Width;
    canvas.height = HTML_Height;

    // Set background color
    context.fillStyle = "#ffffff"; // White background
    context.fillRect(0, 0, canvas.width, canvas.height);

    // Render HTML content to canvas
    html2canvas(contentElement, { canvas: canvas }).then(function (canvas) {
        var imgData = canvas.toDataURL("image/jpeg", 1.0);
        var pdf = new jsPDF('p', 'pt', [PDF_Width, PDF_Height]);

        // Add the image with the background color
        pdf.addImage(imgData, 'JPEG', top_left_margin, top_left_margin, HTML_Width, HTML_Height);

        // Save the PDF locally
        pdf.save("patient_report.pdf");

        // Send the PDF to the server
        var pdfBlob = pdf.output('blob');
        var mrNumber = document.getElementById('mr_number').value; // Get MR number

        var formData = new FormData();
        formData.append('pdf', pdfBlob, 'patient_report.pdf');
        formData.append('mr_number', mrNumber); // Append MR number

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
    });
}
