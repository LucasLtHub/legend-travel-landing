<?php
/**
 * sorteo-submit.php — recibe las participaciones del sorteo de Río.
 *
 *  - Valida todos los campos del lado del servidor.
 *  - Anti-spam: campo trampa (honeypot) + rechazo de envíos a menos de 3 s
 *    de haber cargado la página.
 *  - Guarda cada participación como una fila de CSV en una carpeta que NO
 *    es accesible por URL: primero intenta FUERA del docroot
 *    (…/sorteo-data/, hermana de public_html); si no puede, usa
 *    sorteo/data/ protegida con .htaccess "Deny from all".
 *  - Deduplica por email.
 *  - Avisa por mail a NOTIFICAR; si mail() falla no bloquea: el CSV es la
 *    fuente de verdad y el fallo queda anotado en el log.
 *
 * Respuesta: JSON {ok:true} o {ok:false, code, msg}.
 */
declare(strict_types=1);
ini_set('display_errors', '0');   // nunca mezclar avisos de PHP con la respuesta JSON
error_reporting(E_ALL);

const NOTIFICAR = 'lucas@legendtravel.com.ar';
const REMITENTE = 'no-reply@legendtravel.com.ar';
const CSV_NOMBRE = 'sorteo-rio-participantes.csv';
const DESTINOS = ['Caribe', 'Brasil', 'Europa', 'USA y Disney', 'Argentina', 'Cruceros', 'Otro'];
const CUANDO = ['En los próximos 6 meses', 'Este año', 'En 2027', 'Todavía no lo sé'];

header('Content-Type: application/json; charset=utf-8');
header('X-Robots-Tag: noindex, nofollow');
header('Cache-Control: no-store');

function responder(bool $ok, string $code = '', string $msg = ''): void {
    echo json_encode(['ok' => $ok, 'code' => $code, 'msg' => $msg], JSON_UNESCAPED_UNICODE);
    exit;
}
function campo(string $k): string {
    $v = $_POST[$k] ?? '';
    return is_string($v) ? trim($v) : '';
}

if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') {
    http_response_code(405);
    responder(false, 'method', 'Método no permitido.');
}

/* ---- anti-spam ---- */
if (campo('website') !== '') {            // campo trampa: un humano nunca lo completa
    responder(true);                        // se le responde "ok" para no dar pistas
}
$t = (int) campo('t');                     // momento en que se cargó la página (ms)
$ahora = (int) round(microtime(true) * 1000);
if ($t <= 0 || ($ahora - $t) < 3000) {
    responder(false, 'spam', 'Esperá un momento y volvé a intentar.');
}

/* ---- validación ---- */
$nombre = campo('nombre');
$email = strtolower(campo('email'));
$whatsapp = campo('whatsapp');
$instagram = ltrim(campo('instagram'), '@');
$destino = campo('destino');
$cuando = campo('cuando');
$acepto = campo('acepto');

$errores = [];
if (strlen($nombre) < 2 || strlen($nombre) > 120) $errores['nombre'] = 'Ingresá tu nombre y apellido.';
if (!filter_var($email, FILTER_VALIDATE_EMAIL) || strlen($email) > 120) $errores['email'] = 'Revisá el email.';
$digitos = preg_replace('/\D+/', '', $whatsapp);
if (strlen($digitos) < 8 || strlen($digitos) > 20) $errores['whatsapp'] = 'Ingresá tu WhatsApp con código de área.';
if (!preg_match('/^[A-Za-z0-9._]{1,30}$/', $instagram)) $errores['instagram'] = 'Ingresá tu usuario de Instagram.';
if (!in_array($destino, DESTINOS, true)) $errores['destino'] = 'Elegí un destino.';
if (!in_array($cuando, CUANDO, true)) $errores['cuando'] = 'Elegí una opción.';
if ($acepto !== 'si') $errores['acepto'] = 'Tenés que aceptar las bases.';
if ($errores) {
    echo json_encode(['ok' => false, 'code' => 'invalid', 'msg' => 'Revisá los datos marcados.', 'campos' => $errores], JSON_UNESCAPED_UNICODE);
    exit;
}

/* ---- carpeta de datos (nunca pública) ---- */
function carpeta_datos(): ?string {
    $cands = [];
    $doc = rtrim((string) ($_SERVER['DOCUMENT_ROOT'] ?? ''), '/\\');
    if ($doc !== '' && dirname($doc) !== $doc) $cands[] = dirname($doc) . DIRECTORY_SEPARATOR . 'sorteo-data';
    $cands[] = __DIR__ . DIRECTORY_SEPARATOR . 'data';
    foreach ($cands as $dir) {
        if (!is_dir($dir)) @mkdir($dir, 0750, true);
        if (!is_dir($dir) || !is_writable($dir)) continue;
        // cinturón y tiradores: aunque la carpeta quede dentro del docroot, Apache no la sirve
        if (!file_exists($dir . '/.htaccess')) @file_put_contents($dir . '/.htaccess', "Require all denied\nDeny from all\n");
        if (!file_exists($dir . '/index.html')) @file_put_contents($dir . '/index.html', '');
        return $dir;
    }
    return null;
}
$dir = carpeta_datos();
if ($dir === null) {
    http_response_code(500);
    responder(false, 'storage', 'No pudimos guardar tu participación. Escribinos por WhatsApp y la registramos a mano.');
}
$csv = $dir . DIRECTORY_SEPARATOR . CSV_NOMBRE;
$log = $dir . DIRECTORY_SEPARATOR . 'sorteo-rio.log';

/* ---- guardar (con bloqueo) y deduplicar por email ---- */
$fh = fopen($csv, 'c+');
if ($fh === false) {
    http_response_code(500);
    responder(false, 'storage', 'No pudimos guardar tu participación. Escribinos por WhatsApp y la registramos a mano.');
}
flock($fh, LOCK_EX);
$nuevo = fstat($fh)['size'] === 0;
$duplicado = false;
if (!$nuevo) {
    rewind($fh);
    while (($fila = fgetcsv($fh)) !== false) {
        if (isset($fila[2]) && strtolower(trim($fila[2])) === $email) { $duplicado = true; break; }
    }
}
if ($duplicado) {
    flock($fh, LOCK_UN); fclose($fh);
    responder(false, 'dup', 'Ese email ya está participando. ¡Mucha suerte! El 28/10 anunciamos al ganador en nuestras stories.');
}
fseek($fh, 0, SEEK_END);
if ($nuevo) fputcsv($fh, ['fecha', 'nombre', 'email', 'whatsapp', 'instagram', 'destino', 'cuando', 'acepto']);
$fecha = date('Y-m-d H:i:s');
fputcsv($fh, [$fecha, $nombre, $email, $whatsapp, '@' . $instagram, $destino, $cuando, 'si']);
fflush($fh);
flock($fh, LOCK_UN);
fclose($fh);

/* ---- aviso por mail (no bloquea) ---- */
$asunto = 'Sorteo Río — nueva participación: ' . $nombre;
$cuerpo = "Nueva participación en el sorteo de Río de Janeiro\n\n"
    . "Fecha: $fecha\nNombre: $nombre\nEmail: $email\nWhatsApp: $whatsapp\nInstagram: @$instagram\n"
    . "Destino soñado: $destino\nCuándo: $cuando\nAcepta bases y novedades: sí\n\n"
    . "CSV: $csv\n";
$cabeceras = 'From: Legend Travel <' . REMITENTE . ">\r\nReply-To: $email\r\nContent-Type: text/plain; charset=UTF-8\r\n";
$enviado = false;
try {
    $enviado = @mail(NOTIFICAR, '=?UTF-8?B?' . base64_encode($asunto) . '?=', $cuerpo, $cabeceras);
} catch (Throwable $e) { $enviado = false; }
@file_put_contents($log, "$fecha\t$email\tmail=" . ($enviado ? 'ok' : 'FALLO') . "\n", FILE_APPEND);

responder(true);
