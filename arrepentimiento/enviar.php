<?php
/**
 * arrepentimiento/enviar.php — recibe el formulario del botón de arrepentimiento
 * (Ley 24.240, art. 34 / Res. 424/2020) y lo envía por mail a NOTIFICAR.
 *
 *  - Valida del lado del servidor; campo trampa + rechazo de envíos a <3 s.
 *  - Cada solicitud queda también en un CSV (fecha, nombre, email, teléfono,
 *    reserva, mensaje) en una carpeta que NO es accesible por URL: primero
 *    fuera del docroot (../sorteo-data/, la misma que usa el sorteo) y, si no
 *    se puede, en arrepentimiento/data/ protegida con .htaccess.
 *  - Si mail() falla no bloquea: el CSV es la fuente de verdad y el fallo
 *    queda en el log.
 * Respuesta: JSON {ok:true, numero} o {ok:false, code, msg, campos}.
 */
declare(strict_types=1);
ini_set('display_errors', '0');
error_reporting(E_ALL);

const NOTIFICAR = 'lucas@legendtravel.com.ar';
const REMITENTE = 'no-reply@legendtravel.com.ar';
const CSV_NOMBRE = 'arrepentimiento-solicitudes.csv';

header('Content-Type: application/json; charset=utf-8');
header('X-Robots-Tag: noindex, nofollow');
header('Cache-Control: no-store');

function responder(bool $ok, string $code = '', string $msg = '', array $extra = []): void {
    echo json_encode(array_merge(['ok' => $ok, 'code' => $code, 'msg' => $msg], $extra), JSON_UNESCAPED_UNICODE);
    exit;
}
function campo(string $k): string { $v = $_POST[$k] ?? ''; return is_string($v) ? trim($v) : ''; }

if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') { http_response_code(405); responder(false, 'method', 'Método no permitido.'); }
if (campo('website') !== '') responder(true, '', '', ['numero' => 'AR-0']);   // campo trampa
$t = (int) campo('t'); $ahora = (int) round(microtime(true) * 1000);
if ($t <= 0 || ($ahora - $t) < 3000) responder(false, 'spam', 'Esperá un momento y volvé a intentar.');

$nombre = campo('nombre'); $email = strtolower(campo('email')); $telefono = campo('telefono');
$reserva = campo('reserva'); $mensaje = campo('mensaje'); $acepto = campo('acepto');
$errores = [];
if (strlen($nombre) < 2 || strlen($nombre) > 120) $errores['nombre'] = 'Ingresá tu nombre y apellido.';
if (!filter_var($email, FILTER_VALIDATE_EMAIL) || strlen($email) > 120) $errores['email'] = 'Revisá el email.';
$dig = preg_replace('/\D+/', '', $telefono);
if (strlen($dig) < 8 || strlen($dig) > 20) $errores['telefono'] = 'Ingresá un teléfono con código de área.';
if (strlen($reserva) < 3 || strlen($reserva) > 300) $errores['reserva'] = 'Indicá el número de reserva o qué contrataste.';
if (strlen($mensaje) < 10 || strlen($mensaje) > 3000) $errores['mensaje'] = 'Contanos brevemente tu solicitud.';
if ($acepto !== 'si') $errores['acepto'] = 'Tenés que confirmar que los datos son correctos.';
if ($errores) { echo json_encode(['ok' => false, 'code' => 'invalid', 'msg' => 'Revisá los datos marcados.', 'campos' => $errores], JSON_UNESCAPED_UNICODE); exit; }

function carpeta_datos(): ?string {
    $cands = [];
    $doc = rtrim((string) ($_SERVER['DOCUMENT_ROOT'] ?? ''), '/\\');
    if ($doc !== '' && dirname($doc) !== $doc) $cands[] = dirname($doc) . DIRECTORY_SEPARATOR . 'sorteo-data';
    $cands[] = __DIR__ . DIRECTORY_SEPARATOR . 'data';
    foreach ($cands as $dir) {
        if (!is_dir($dir)) @mkdir($dir, 0750, true);
        if (!is_dir($dir) || !is_writable($dir)) continue;
        if (!file_exists($dir . '/.htaccess')) @file_put_contents($dir . '/.htaccess', "Require all denied\nDeny from all\n");
        if (!file_exists($dir . '/index.html')) @file_put_contents($dir . '/index.html', '');
        return $dir;
    }
    return null;
}
$dir = carpeta_datos();
if ($dir === null) { http_response_code(500); responder(false, 'storage', 'No pudimos registrar la solicitud. Escribinos a ' . NOTIFICAR . ' o por WhatsApp.'); }
$csv = $dir . DIRECTORY_SEPARATOR . CSV_NOMBRE; $log = $dir . DIRECTORY_SEPARATOR . 'arrepentimiento.log';
$fh = fopen($csv, 'c+');
if ($fh === false) { http_response_code(500); responder(false, 'storage', 'No pudimos registrar la solicitud. Escribinos a ' . NOTIFICAR . ' o por WhatsApp.'); }
flock($fh, LOCK_EX);
$nuevo = fstat($fh)['size'] === 0; $n = 0;
if (!$nuevo) { rewind($fh); while (fgetcsv($fh) !== false) $n++; $n--; }
fseek($fh, 0, SEEK_END);
if ($nuevo) fputcsv($fh, ['numero', 'fecha', 'nombre', 'email', 'telefono', 'reserva', 'mensaje']);
$numero = 'AR-' . date('Ymd') . '-' . str_pad((string) ($n + 1), 3, '0', STR_PAD_LEFT);
$fecha = date('Y-m-d H:i:s');
fputcsv($fh, [$numero, $fecha, $nombre, $email, $telefono, $reserva, $mensaje]);
fflush($fh); flock($fh, LOCK_UN); fclose($fh);

$asunto = 'Botón de arrepentimiento — ' . $numero . ' — ' . $nombre;
$cuerpo = "Nueva solicitud de arrepentimiento\n\nNúmero: $numero\nFecha: $fecha\nNombre: $nombre\nEmail: $email\nTeléfono: $telefono\nReserva / compra: $reserva\n\nMensaje:\n$mensaje\n\nCSV: $csv\n";
$cab = 'From: Legend Travel <' . REMITENTE . ">\r\nReply-To: $email\r\nContent-Type: text/plain; charset=UTF-8\r\n";
$enviado = false;
try { $enviado = @mail(NOTIFICAR, '=?UTF-8?B?' . base64_encode($asunto) . '?=', $cuerpo, $cab); } catch (Throwable $e) { $enviado = false; }
// acuse al solicitante (si sale): le deja constancia del número
try { @mail($email, '=?UTF-8?B?' . base64_encode('Recibimos tu solicitud de arrepentimiento (' . $numero . ')') . '?=', "Hola $nombre,\n\nRecibimos tu solicitud de arrepentimiento con el número $numero el $fecha. En las próximas 24 horas hábiles te respondemos a este mail con los pasos a seguir.\n\nLegend Travel SRL · Legajo 7553\nParaná 3745, Martínez, Buenos Aires\n", 'From: Legend Travel <' . REMITENTE . ">\r\nContent-Type: text/plain; charset=UTF-8\r\n"); } catch (Throwable $e) {}
@file_put_contents($log, "$fecha\t$numero\t$email\tmail=" . ($enviado ? 'ok' : 'FALLO') . "\n", FILE_APPEND);
responder(true, '', '', ['numero' => $numero]);
