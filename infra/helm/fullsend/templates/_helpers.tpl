{{/* Chart name, truncated to the 63-character DNS label limit. */}}
{{- define "fullsend.name" -}}
{{- .Chart.Name | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/* Full name: release-chart, unless the release name already contains the chart name. */}}
{{- define "fullsend.fullname" -}}
{{- if contains .Chart.Name .Release.Name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name .Chart.Name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{/* Labels every object carries (Kubernetes recommended labels). */}}
{{- define "fullsend.labels" -}}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" }}
{{ include "fullsend.selectorLabels" . }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{/* Labels used in selectors. These must never change after the first install. */}}
{{- define "fullsend.selectorLabels" -}}
app.kubernetes.io/name: {{ include "fullsend.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}
