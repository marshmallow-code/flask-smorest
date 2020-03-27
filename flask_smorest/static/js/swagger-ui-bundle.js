window.onload = function() {
    const ui = SwaggerUIBundle({
        url: document.getElementById('openapi-url').textContent,
        dom_id: '#swagger-ui-container',
        deepLinking: true,
        layout: "BaseLayout",
        supportedSubmitMethods: JSON.parse(document.getElementById('supported-submit-methods').textContent),
    })
    window.ui = ui
}
