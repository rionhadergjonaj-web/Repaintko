import { DatabaseSync } from 'node:sqlite';
import { mkdirSync } from 'node:fs';
import { dirname } from 'node:path';
import { randomBytes, scrypt, timingSafeEqual, createHash } from 'node:crypto';
import { promisify } from 'node:util';
const derive = promisify(scrypt);
export const digest = value => createHash('sha256').update(value).digest('hex');
export function openDatabase(path) {
  if (path !== ':memory:') mkdirSync(dirname(path), {recursive:true});
  const db = new DatabaseSync(path);
  db.exec(`PRAGMA journal_mode=WAL; PRAGMA foreign_keys=ON; PRAGMA busy_timeout=5000;
    CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, name TEXT NOT NULL, name_key TEXT NOT NULL UNIQUE, password TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'user' CHECK(role IN ('user','admin')));
    CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), expires INTEGER NOT NULL);
    CREATE TABLE IF NOT EXISTS suggestions(id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), title TEXT NOT NULL, body TEXT NOT NULL, created INTEGER NOT NULL, status TEXT NOT NULL DEFAULT 'new' CHECK(status IN ('new','reviewing','planned','done')));`);
  return db;
}
export function username(raw) {
  if (typeof raw !== 'string' || !/^[A-Za-z0-9_]{5,24}$/.test(raw)) throw new Error('Benutzername: 5–24 Zeichen, nur Buchstaben A–Z, Zahlen und Unterstrich.');
  return {name:raw,key:raw.toLowerCase()};
}
export function passwordValid(password) { return typeof password === 'string' && password.length >= 12 && password.length <= 128; }
export async function hashPassword(password) {
  const salt=randomBytes(16).toString('hex');
  const hash=await derive(password,salt,64,{N:32768,r:8,p:1,maxmem:64*1024*1024});
  return `${salt}:${hash.toString('hex')}`;
}
export async function checkPassword(password,stored) {
  const [salt,hex]=stored.split(':');
  const hash=await derive(password,salt,64,{N:32768,r:8,p:1,maxmem:64*1024*1024});
  return timingSafeEqual(hash,Buffer.from(hex,'hex'));
}
export async function provisionAdmin(db,password) {
  if(!passwordValid(password)) throw new Error('Admin-Passwort muss 12–128 Zeichen haben.');
  if(db.prepare('SELECT id FROM users WHERE name_key=?').get('rezzko')) throw new Error('Rezzko existiert bereits. Kein Konto wurde überschrieben.');
  db.prepare('INSERT INTO users(name,name_key,password,role) VALUES(?,?,?,?)').run('Rezzko','rezzko',await hashPassword(password),'admin');
}
