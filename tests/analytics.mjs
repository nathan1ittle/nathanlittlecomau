import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';

// Run the actual exported embed with a fake HubSpot/GA environment. No network or CRM writes.
const html = readFileSync(new URL('../contact.html', import.meta.url), 'utf8');
const script = [...html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/g)]
  .map(match => match[1]).find(source => source.includes('hbspt.forms.create'));
assert.ok(script, 'contact form embed exists');
let config;
const calls = [];
const context = { hbspt: { forms: { create(value) { config = value; } } },
  window: { gtag(...args) { calls.push(args); } } };
vm.runInNewContext(script, context);
assert.equal(calls.length, 0, 'loading or viewing a form is not a lead');
assert.equal(config.onFormSubmit, undefined, 'no pre-submission conversion');
config.onFormSubmitted(null, { submissionValues: { email: 'private@example.test', message: 'private' } });
assert.equal(calls.length, 1, 'one event per success callback');
assert.equal(calls[0][0], 'event');
assert.equal(calls[0][1], 'generate_lead');
assert.deepEqual(JSON.parse(JSON.stringify(calls[0][2])), {
  send_to: 'G-G27YDPP6Y2', form_id: config.formId, transport_type: 'beacon'
});
context.window.gtag = undefined;
assert.doesNotThrow(() => config.onFormSubmitted(), 'blocked analytics does not break forms');
context.window.gtag = () => { throw new Error('blocked'); };
assert.doesNotThrow(() => config.onFormSubmitted(), 'analytics errors do not break forms');
console.log('Confirmed-enquiry callback tests passed (no external submissions).');
