import {expect, test} from '@playwright/test';
import {makeProject, mockApi} from './fixtures';

test.describe('Данные к требованиям', () => {
  test('приложенные файлы видны, новые уходят телом запроса, неверный формат объяснён', async ({page}) => {
    const project = makeProject('Заявки на ремонт');
    const api = await mockApi(page, {projects: [project], attachments: [{name: 'offices.csv', size: 2048}]});
    await page.goto(`/projects/${project.id}/flow`);

    const section = page.getByRole('region', {name: 'Данные к требованиям'});
    await expect(section).toContainText('offices.csv');

    const geojson = JSON.stringify({type: 'FeatureCollection', features: []});
    await page.getByTestId('run.attach').setInputFiles([
      {name: 'spb.geojson', mimeType: 'application/geo+json', buffer: Buffer.from(geojson)},
      {name: 'notes.txt', mimeType: 'text/plain', buffer: Buffer.from('Рабочие часы 9–18')},
    ]);
    await expect(section).toContainText('spb.geojson');
    await expect(section).toContainText('notes.txt');
    await expect(page.getByRole('region', {name: 'Уведомления'})).toContainText('Файл notes.txt приложен');

    // Файлы уходят по одному, сам файл — тело запроса, имя — параметр.
    const uploads = api.requests.filter(r => r.method === 'POST' && r.url.includes('/attachments'));
    expect(uploads.map(r => (r.body as {name: string}).name)).toEqual(['spb.geojson', 'notes.txt']);
    expect(uploads[0].body).toEqual({name: 'spb.geojson', size: geojson.length, type: 'application/octet-stream'});
    expect(uploads[0].url).toContain(`/api/projects/${project.id}/attachments?name=spb.geojson`);

    await page.getByTestId('run.attach').setInputFiles({name: 'setup.exe', mimeType: 'application/octet-stream', buffer: Buffer.from('MZ')});
    await expect(page.getByRole('region', {name: 'Уведомления'})).toContainText('Не удалось приложить setup.exe');
    await expect(page.getByRole('region', {name: 'Уведомления'})).toContainText('форматы json, geojson, csv');
    await expect(section).not.toContainText('setup.exe');
  });
});
