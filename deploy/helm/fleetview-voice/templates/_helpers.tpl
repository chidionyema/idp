{{/*
Expand the name of the chart.
*/}}
{{- define "fleetview-voice.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "fleetview-voice.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "fleetview-voice.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "fleetview-voice.labels" -}}
helm.sh/chart: {{ include "fleetview-voice.chart" . }}
{{ include "fleetview-voice.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "fleetview-voice.selectorLabels" -}}
app.kubernetes.io/name: {{ include "fleetview-voice.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
API component labels
*/}}
{{- define "fleetview-voice.api.labels" -}}
{{ include "fleetview-voice.labels" . }}
app.kubernetes.io/component: api
{{- end }}

{{/*
API selector labels
*/}}
{{- define "fleetview-voice.api.selectorLabels" -}}
{{ include "fleetview-voice.selectorLabels" . }}
app.kubernetes.io/component: api
{{- end }}

{{/*
Worker component labels
*/}}
{{- define "fleetview-voice.worker.labels" -}}
{{ include "fleetview-voice.labels" . }}
app.kubernetes.io/component: worker
{{- end }}

{{/*
Worker selector labels
*/}}
{{- define "fleetview-voice.worker.selectorLabels" -}}
{{ include "fleetview-voice.selectorLabels" . }}
app.kubernetes.io/component: worker
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "fleetview-voice.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "fleetview-voice.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Return the NATS URL
*/}}
{{- define "fleetview-voice.natsUrl" -}}
{{- if .Values.eventBus.nats.url }}
{{- .Values.eventBus.nats.url }}
{{- else if .Values.nats.enabled }}
{{- printf "nats://%s-nats:4222" .Release.Name }}
{{- else }}
{{- fail "NATS URL must be provided when using NATS event bus and bundled NATS is disabled" }}
{{- end }}
{{- end }}

{{/*
Return the Kafka brokers as a comma-separated string
*/}}
{{- define "fleetview-voice.kafkaBrokers" -}}
{{- join "," .Values.eventBus.kafka.brokers }}
{{- end }}

{{/*
Return the Redis URL
*/}}
{{- define "fleetview-voice.redisUrl" -}}
{{- if .Values.redis.enabled }}
{{- printf "redis://%s-redis-master:6379" .Release.Name }}
{{- else }}
{{- "" }}
{{- end }}
{{- end }}

{{/*
Return the image name
*/}}
{{- define "fleetview-voice.image" -}}
{{- $registryName := .Values.global.imageRegistry | default "" -}}
{{- $repositoryName := .Values.image.repository -}}
{{- $tag := .Values.image.tag | default .Chart.AppVersion -}}
{{- if $registryName }}
{{- printf "%s/%s:%s" $registryName $repositoryName $tag }}
{{- else }}
{{- printf "%s:%s" $repositoryName $tag }}
{{- end }}
{{- end }}

{{/*
Return image pull secrets
*/}}
{{- define "fleetview-voice.imagePullSecrets" -}}
{{- $pullSecrets := list }}
{{- if .Values.global.imagePullSecrets }}
{{- range .Values.global.imagePullSecrets }}
{{- $pullSecrets = append $pullSecrets . }}
{{- end }}
{{- end }}
{{- if .Values.imagePullSecrets }}
{{- range .Values.imagePullSecrets }}
{{- $pullSecrets = append $pullSecrets . }}
{{- end }}
{{- end }}
{{- if $pullSecrets }}
imagePullSecrets:
{{- range $pullSecrets }}
  - name: {{ . }}
{{- end }}
{{- end }}
{{- end }}
