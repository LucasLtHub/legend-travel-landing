<?php
/**
 * newsletter-config.example.php — MODELO de la configuración de Doppler (sin la clave).
 *
 * El archivo real se llama newsletter-config.php y NUNCA va al repo ni a public_html:
 *   - Producción (Hostinger): en la carpeta que contiene public_html, al lado de
 *     sorteo-data/  →  …/domains/legendtravel.com.ar/newsletter-config.php
 *   - Pruebas locales: newsletter/newsletter-config.php (está en .gitignore).
 *
 * suscribir.php lo busca en ese orden. Si no lo encuentra, los emails no se pierden:
 * quedan en newsletter-data/pendientes.csv y llega un aviso por mail.
 */
return [
    'cuenta'  => 'EMAIL-CON-EL-QUE-SE-ENTRA-A-DOPPLER',   // el "accountName" de la API
    'api_key' => 'PEGAR-ACA-LA-API-KEY',                  // Doppler → Panel de control → API y Webhooks
];
